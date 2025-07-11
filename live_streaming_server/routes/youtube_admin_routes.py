from flask import Blueprint, request, jsonify, redirect, session
from flask_jwt_extended import jwt_required, get_jwt_identity
import os
import sys
from datetime import datetime

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from common.database import db
from common.response import success_response, error_response
from auth.models.models import User, UserRole
from auth.utils import super_admin_role_required
from models.youtube_token import YouTubeToken
from live_streaming_server.services.youtube_live_service import YouTubeLiveService

youtube_admin_bp = Blueprint('youtube_admin', __name__)

@youtube_admin_bp.route('/oauth/initiate', methods=['POST'])
@jwt_required()
@super_admin_role_required
def initiate_youtube_oauth():
    """Initiate YouTube OAuth flow for SuperAdmin."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        # Get redirect URI from request or use default
        data = request.get_json() or {}
        redirect_uri = data.get('redirect_uri')
        
        youtube_service = YouTubeLiveService()
        auth_url = youtube_service.get_authorization_url(redirect_uri)
        
        # Store user_id in session for callback
        session['oauth_user_id'] = user_id
        
        return success_response('OAuth URL generated successfully', {
            'authorization_url': auth_url,
            'instructions': 'Visit the authorization URL to grant YouTube permissions'
        })
        
    except Exception as e:
        return error_response(f'Error initiating OAuth: {str(e)}', 500)

@youtube_admin_bp.route('/oauth/callback', methods=['GET'])
def youtube_oauth_callback():
    """Handle YouTube OAuth callback."""
    try:
        code = request.args.get('code')
        error = request.args.get('error')
        
        if error:
            return error_response(f'OAuth error: {error}', 400)
        
        if not code:
            return error_response('Authorization code not received', 400)
        
        # Get user_id from session
        user_id = session.get('oauth_user_id')
        if not user_id:
            return error_response('Session expired. Please restart OAuth flow.', 400)
        
        user = User.query.get(user_id)
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        youtube_service = YouTubeLiveService()
        
        # Exchange code for tokens
        token_data = youtube_service.exchange_code_for_tokens(code)
        
        # Store tokens in database
        youtube_token = youtube_service.store_tokens(token_data, user_id)
        
        # Clear session
        session.pop('oauth_user_id', None)
        
        # Return success page or redirect to dashboard
        return f"""
        <html>
        <head>
            <title>YouTube OAuth Success</title>
            <style>
                body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; }}
                .success {{ color: green; }}
                .info {{ background: #f0f8ff; padding: 20px; border-radius: 5px; margin: 20px; }}
            </style>
        </head>
        <body>
            <h1 class="success">✅ YouTube OAuth Successful!</h1>
            <div class="info">
                <p><strong>YouTube integration has been configured successfully.</strong></p>
                <p>Token expires on: {youtube_token.expires_at.strftime('%Y-%m-%d %H:%M:%S') if youtube_token.expires_at else 'N/A'}</p>
                <p>You can now close this window and return to the SuperAdmin dashboard.</p>
            </div>
            <script>
                // Auto-close after 5 seconds
                setTimeout(function() {{
                    window.close();
                }}, 5000);
            </script>
        </body>
        </html>
        """
        
    except Exception as e:
        return error_response(f'Error processing OAuth callback: {str(e)}', 500)

@youtube_admin_bp.route('/status', methods=['GET'])
@jwt_required()
@super_admin_role_required
def get_youtube_status():
    """Get YouTube token status for SuperAdmin."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        youtube_service = YouTubeLiveService()
        status = youtube_service.get_token_status()
        
        return success_response('YouTube status retrieved successfully', status)
        
    except Exception as e:
        return error_response(f'Error getting YouTube status: {str(e)}', 500)

@youtube_admin_bp.route('/token/refresh', methods=['POST'])
@jwt_required()
@super_admin_role_required
def refresh_youtube_token():
    """Manually refresh YouTube token."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        youtube_service = YouTubeLiveService()
        credentials = youtube_service.get_valid_credentials()
        
        if not credentials:
            return error_response('No valid credentials found. Please re-authenticate.', 400)
        
        return success_response('Token refreshed successfully', {
            'message': 'YouTube token has been refreshed'
        })
        
    except Exception as e:
        return error_response(f'Error refreshing token: {str(e)}', 500)

@youtube_admin_bp.route('/token/revoke', methods=['DELETE'])
@jwt_required()
@super_admin_role_required
def revoke_youtube_token():
    """Revoke/delete YouTube token."""
    try:
        user_id = get_jwt_identity()
        user = User.query.get(user_id)
        
        if not user or user.role != UserRole.SUPER_ADMIN:
            return error_response('Unauthorized. SuperAdmin access required.', 403)
        
        # Deactivate all tokens
        YouTubeToken.deactivate_all_tokens()
        
        return success_response('YouTube token revoked successfully', {
            'message': 'All YouTube tokens have been deactivated'
        })
        
    except Exception as e:
        return error_response(f'Error revoking token: {str(e)}', 500)
