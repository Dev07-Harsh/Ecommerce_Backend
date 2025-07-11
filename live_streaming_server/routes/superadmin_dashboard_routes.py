from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import sys
from datetime import datetime, timedelta

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.database import db
from common.response import success_response, error_response
from auth.models.models import User, UserRole
from auth.utils import super_admin_role_required
from models.youtube_token import YouTubeToken
from live_streaming_server.services.youtube_live_service import YouTubeLiveService

superadmin_dashboard_bp = Blueprint('superadmin_dashboard', __name__)

@superadmin_dashboard_bp.route('/youtube/status', methods=['GET'])
@jwt_required()
@super_admin_role_required
def get_youtube_dashboard_status():
    """Get YouTube status for SuperAdmin dashboard with notification alerts."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        youtube_service = YouTubeLiveService()
        status = youtube_service.get_token_status()
        
        # Add dashboard-specific information
        dashboard_data = {
            'youtube_integration': status,
            'notifications': [],
            'actions_required': []
        }
        
        # Check for notifications and required actions
        if status['status'] == 'no_token':
            dashboard_data['notifications'].append({
                'type': 'warning',
                'title': 'YouTube Integration Not Configured',
                'message': 'YouTube Live integration is not set up. Merchants cannot create YouTube events.',
                'severity': 'medium'
            })
            dashboard_data['actions_required'].append({
                'action': 'configure_youtube',
                'title': 'Configure YouTube Integration',
                'description': 'Set up YouTube OAuth to enable live streaming integration'
            })
            
        elif status['status'] == 'expired':
            dashboard_data['notifications'].append({
                'type': 'error',
                'title': 'YouTube Token Expired',
                'message': 'YouTube access token has expired. Merchants cannot create YouTube events.',
                'severity': 'high'
            })
            dashboard_data['actions_required'].append({
                'action': 'renew_youtube_token',
                'title': 'Renew YouTube Token',
                'description': 'Re-authenticate with YouTube to restore functionality'
            })
            
        elif status['status'] == 'expiring_soon':
            token_info = status.get('token_info', {})
            days_left = token_info.get('days_until_expiry', 0)
            
            dashboard_data['notifications'].append({
                'type': 'warning',
                'title': 'YouTube Token Expiring Soon',
                'message': f'YouTube token expires in {days_left} day(s). Consider renewing to avoid service interruption.',
                'severity': 'medium'
            })
            dashboard_data['actions_required'].append({
                'action': 'renew_youtube_token',
                'title': 'Renew YouTube Token',
                'description': f'Token expires in {days_left} day(s). Renew now to avoid interruption.'
            })
        
        return success_response('YouTube dashboard status retrieved successfully', dashboard_data)
        
    except Exception as e:
        return error_response(f'Error getting YouTube dashboard status: {str(e)}', 500)

@superadmin_dashboard_bp.route('/youtube/configure', methods=['POST'])
@jwt_required()
@super_admin_role_required
def configure_youtube_integration():
    """Start YouTube OAuth configuration process."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        # Get frontend URL for proper redirect
        data = request.get_json() or {}
        frontend_url = data.get('frontend_url', 'http://localhost:5173')
        
        youtube_service = YouTubeLiveService()
        
        # Generate OAuth URL
        auth_url = youtube_service.get_authorization_url()
        
        return success_response('YouTube OAuth URL generated', {
            'oauth_url': auth_url,
            'instructions': [
                '1. Click the OAuth URL to open YouTube authentication',
                '2. Sign in with the platform\'s YouTube account',
                '3. Grant the required permissions',
                '4. You will be redirected back automatically',
                '5. The integration will be active immediately'
            ],
            'estimated_time': '2-3 minutes'
        })
        
    except Exception as e:
        return error_response(f'Error configuring YouTube integration: {str(e)}', 500)

@superadmin_dashboard_bp.route('/youtube/test-connection', methods=['POST'])
@jwt_required()
@super_admin_role_required
def test_youtube_connection():
    """Test YouTube API connection and credentials."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        youtube_service = YouTubeLiveService()
        credentials = youtube_service.get_valid_credentials()
        
        if not credentials:
            return error_response('No valid YouTube credentials found', 400)
        
        # Try to make a simple API call to test the connection
        try:
            from googleapiclient.discovery import build
            youtube = build('youtube', 'v3', credentials=credentials)
            
            # Get channel info to test the connection
            response = youtube.channels().list(
                part='snippet,statistics',
                mine=True
            ).execute()
            
            if response.get('items'):
                channel = response['items'][0]
                channel_info = {
                    'channel_name': channel['snippet']['title'],
                    'subscriber_count': channel['statistics'].get('subscriberCount', 'Hidden'),
                    'video_count': channel['statistics'].get('videoCount', '0'),
                    'view_count': channel['statistics'].get('viewCount', '0')
                }
                
                return success_response('YouTube connection test successful', {
                    'status': 'connected',
                    'channel_info': channel_info,
                    'test_time': datetime.utcnow().isoformat()
                })
            else:
                return error_response('No YouTube channel found for this account', 400)
                
        except Exception as api_error:
            return error_response(f'YouTube API test failed: {str(api_error)}', 400)
        
    except Exception as e:
        return error_response(f'Error testing YouTube connection: {str(e)}', 500)

@superadmin_dashboard_bp.route('/youtube/stats', methods=['GET'])
@jwt_required()
@super_admin_role_required
def get_youtube_integration_stats():
    """Get statistics about YouTube integration usage."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        # Get statistics from database
        from models.live_stream import LiveStream
        
        # Total streams with YouTube integration
        total_streams_with_youtube = LiveStream.query.filter(
            LiveStream.youtube_event_id.isnot(None),
            LiveStream.deleted_at.is_(None)
        ).count()
        
        # Recent streams (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_streams_with_youtube = LiveStream.query.filter(
            LiveStream.youtube_event_id.isnot(None),
            LiveStream.created_at >= thirty_days_ago,
            LiveStream.deleted_at.is_(None)
        ).count()
        
        # Total streams without YouTube
        total_streams_without_youtube = LiveStream.query.filter(
            LiveStream.youtube_event_id.is_(None),
            LiveStream.deleted_at.is_(None)
        ).count()
        
        # Success rate calculation
        total_streams = total_streams_with_youtube + total_streams_without_youtube
        success_rate = (total_streams_with_youtube / total_streams * 100) if total_streams > 0 else 0
        
        stats = {
            'total_streams_with_youtube': total_streams_with_youtube,
            'total_streams_without_youtube': total_streams_without_youtube,
            'recent_streams_with_youtube': recent_streams_with_youtube,
            'integration_success_rate': round(success_rate, 2),
            'last_updated': datetime.utcnow().isoformat()
        }
        
        return success_response('YouTube integration statistics retrieved', stats)
        
    except Exception as e:
        return error_response(f'Error getting YouTube integration stats: {str(e)}', 500)
