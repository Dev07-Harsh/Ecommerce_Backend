import os
import sys
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request

from config import get_config
from common.database import db
from models.youtube_token import YouTubeToken

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class YouTubeLiveService:
    """Service for managing YouTube Live streams and OAuth authentication."""
    
    def __init__(self):
        self.config = get_config()
        self.scopes = self.config.YOUTUBE_SCOPES
        
    def create_oauth_flow(self, redirect_uri: str = None) -> Flow:
        """Create OAuth flow for YouTube authentication."""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.config.YOUTUBE_CLIENT_ID,
                        "client_secret": self.config.YOUTUBE_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [redirect_uri or self.config.YOUTUBE_REDIRECT_URI]
                    }
                },
                scopes=self.scopes
            )
            flow.redirect_uri = redirect_uri or self.config.YOUTUBE_REDIRECT_URI
            return flow
        except Exception as e:
            logger.error(f"Error creating OAuth flow: {str(e)}")
            raise
    
    def get_authorization_url(self, redirect_uri: str = None) -> str:
        """Get authorization URL for OAuth flow."""
        try:
            flow = self.create_oauth_flow(redirect_uri)
            auth_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                prompt='consent'  # Force consent to get refresh token
            )
            return auth_url
        except Exception as e:
            logger.error(f"Error getting authorization URL: {str(e)}")
            raise
    
    def exchange_code_for_tokens(self, code: str, redirect_uri: str = None) -> Dict:
        """Exchange authorization code for access and refresh tokens."""
        try:
            flow = self.create_oauth_flow(redirect_uri)
            flow.fetch_token(code=code)
            
            credentials = flow.credentials
            
            # Calculate expiry time (typically 1 hour from now, but we'll use the actual expiry)
            expires_at = datetime.utcnow() + timedelta(seconds=credentials.expiry.timestamp() - datetime.utcnow().timestamp()) if credentials.expiry else datetime.utcnow() + timedelta(days=60)
            
            return {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_type': 'Bearer',
                'expires_at': expires_at
            }
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {str(e)}")
            raise
    
    def store_tokens(self, token_data: Dict, created_by: int) -> YouTubeToken:
        """Store YouTube tokens in database."""
        try:
            # Deactivate existing tokens
            YouTubeToken.deactivate_all_tokens()
            
            # Create new token record
            youtube_token = YouTubeToken(
                access_token=token_data['access_token'],
                refresh_token=token_data['refresh_token'],
                token_type=token_data['token_type'],
                expires_at=token_data['expires_at'],
                created_by=created_by,
                is_active=True
            )
            
            db.session.add(youtube_token)
            db.session.commit()
            
            logger.info(f"YouTube tokens stored successfully for user {created_by}")
            return youtube_token
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error storing tokens: {str(e)}")
            raise
    
    def get_valid_credentials(self) -> Optional[Credentials]:
        """Get valid YouTube credentials, refreshing if necessary."""
        try:
            token = YouTubeToken.get_active_token()
            if not token:
                logger.warning("No active YouTube token found")
                return None
            
            if token.is_expired():
                logger.warning("YouTube token has expired")
                return None
            
            credentials = Credentials(
                token=token.access_token,
                refresh_token=token.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.config.YOUTUBE_CLIENT_ID,
                client_secret=self.config.YOUTUBE_CLIENT_SECRET,
                scopes=self.scopes
            )
            
            # Refresh token if needed
            if token.refresh_token_if_needed():
                try:
                    credentials.refresh(Request())
                    
                    # Update token in database
                    token.access_token = credentials.token
                    if credentials.expiry:
                        token.expires_at = credentials.expiry.replace(tzinfo=None)
                    
                    db.session.commit()
                    logger.info("YouTube token refreshed successfully")
                    
                except Exception as e:
                    logger.error(f"Error refreshing token: {str(e)}")
                    return None
            
            return credentials
            
        except Exception as e:
            logger.error(f"Error getting valid credentials: {str(e)}")
            return None
    
    def create_youtube_live_event(self, title: str, description: str, scheduled_time: datetime) -> Optional[Dict]:
        """Create a YouTube Live event."""
        try:
            credentials = self.get_valid_credentials()
            if not credentials:
                logger.error("No valid YouTube credentials available")
                return None
            
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Create the broadcast
            broadcast_body = {
                'snippet': {
                    'title': title,
                    'description': description,
                    'scheduledStartTime': scheduled_time.isoformat() + 'Z'
                },
                'status': {
                    'privacyStatus': 'public',
                    'selfDeclaredMadeForKids': False
                },
                'contentDetails': {
                    'monitorStream': {
                        'enableMonitorStream': False
                    }
                }
            }
            
            broadcast_response = youtube.liveBroadcasts().insert(
                part='snippet,status,contentDetails',
                body=broadcast_body
            ).execute()
            
            broadcast_id = broadcast_response['id']
            
            # Create the stream
            stream_body = {
                'snippet': {
                    'title': f"{title} - Stream"
                },
                'cdn': {
                    'format': '1080p',
                    'ingestionType': 'rtmp'
                }
            }
            
            stream_response = youtube.liveStreams().insert(
                part='snippet,cdn',
                body=stream_body
            ).execute()
            
            stream_id = stream_response['id']
            
            # Bind the stream to the broadcast
            youtube.liveBroadcasts().bind(
                part='id',
                id=broadcast_id,
                streamId=stream_id
            ).execute()
            
            # Get the watch URL
            watch_url = f"https://www.youtube.com/watch?v={broadcast_id}"
            embed_url = f"https://www.youtube.com/embed/{broadcast_id}"
            
            result = {
                'broadcast_id': broadcast_id,
                'stream_id': stream_id,
                'watch_url': watch_url,
                'embed_url': embed_url,
                'stream_url': stream_response['cdn']['ingestionInfo']['streamName'],
                'rtmp_url': stream_response['cdn']['ingestionInfo']['ingestionAddress']
            }
            
            logger.info(f"YouTube Live event created successfully: {broadcast_id}")
            return result
            
        except HttpError as e:
            logger.error(f"YouTube API error: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error creating YouTube Live event: {str(e)}")
            return None
    
    def get_token_status(self) -> Dict:
        """Get status of current YouTube token."""
        try:
            token = YouTubeToken.get_active_token()
            if not token:
                return {
                    'status': 'no_token',
                    'message': 'No YouTube token configured'
                }
            
            if token.is_expired():
                return {
                    'status': 'expired',
                    'message': 'YouTube token has expired',
                    'token_info': token.serialize()
                }
            
            if token.is_expiring_soon():
                return {
                    'status': 'expiring_soon',
                    'message': f'YouTube token expires in {token.get_days_until_expiry()} days',
                    'token_info': token.serialize()
                }
            
            return {
                'status': 'active',
                'message': 'YouTube token is active',
                'token_info': token.serialize()
            }
            
        except Exception as e:
            logger.error(f"Error getting token status: {str(e)}")
            return {
                'status': 'error',
                'message': f'Error checking token status: {str(e)}'
            }
