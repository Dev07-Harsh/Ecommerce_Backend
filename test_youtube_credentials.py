"""
YouTube API Credentials Test Script

This script helps verify that your YouTube API credentials are properly configured.
Run this from the Ecommerce_Backend directory.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_youtube_credentials():
    """Test if YouTube API credentials are properly configured."""
    
    print("🔍 Testing YouTube API Credentials...")
    print("=" * 50)
    
    # Check environment variables
    client_id = os.getenv('YOUTUBE_CLIENT_ID')
    client_secret = os.getenv('YOUTUBE_CLIENT_SECRET')
    redirect_uri = os.getenv('YOUTUBE_REDIRECT_URI')
    
    print(f"✅ Client ID: {'✓ Set' if client_id and client_id != 'your_youtube_client_id_here' else '❌ Not set or default value'}")
    print(f"✅ Client Secret: {'✓ Set' if client_secret and client_secret != 'your_youtube_client_secret_here' else '❌ Not set or default value'}")
    print(f"✅ Redirect URI: {redirect_uri or '❌ Not set'}")
    
    if not client_id or client_id == 'your_youtube_client_id_here':
        print("\n❌ YOUTUBE_CLIENT_ID is not properly configured")
        print("Please update your .env file with the actual Client ID from Google Cloud Console")
        return False
        
    if not client_secret or client_secret == 'your_youtube_client_secret_here':
        print("\n❌ YOUTUBE_CLIENT_SECRET is not properly configured")
        print("Please update your .env file with the actual Client Secret from Google Cloud Console")
        return False
    
    # Test importing required libraries
    print("\n🔍 Testing YouTube API libraries...")
    try:
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import Flow
        from googleapiclient.discovery import build
        print("✅ All YouTube API libraries are available")
    except ImportError as e:
        print(f"❌ Missing library: {e}")
        print("Please run: pip install google-api-python-client google-auth-oauthlib google-auth-httplib2")
        return False
    
    # Test OAuth flow creation
    print("\n🔍 Testing OAuth flow creation...")
    try:
        from live_streaming_server.services.youtube_live_service import YouTubeLiveService
        service = YouTubeLiveService()
        
        # Try to create OAuth flow (this will fail if credentials are wrong)
        flow = service.create_oauth_flow()
        print("✅ OAuth flow created successfully")
        
        # Get authorization URL (this validates the client configuration)
        auth_url = service.get_authorization_url()
        print("✅ Authorization URL generated successfully")
        print(f"🔗 OAuth URL: {auth_url[:100]}...")
        
    except Exception as e:
        print(f"❌ OAuth flow creation failed: {e}")
        if "invalid_client" in str(e).lower():
            print("This usually means:")
            print("1. Client ID or Client Secret is incorrect")
            print("2. The credentials don't exist in Google Cloud Console")
            print("3. The OAuth consent screen is not properly configured")
        return False
    
    print("\n🎉 All tests passed!")
    print("Your YouTube API credentials are properly configured.")
    print("\nNext steps:")
    print("1. Start the live streaming server: python live_streaming_server/app.py")
    print("2. Go to SuperAdmin dashboard > YouTube Integration")
    print("3. Click 'Configure YouTube' to complete OAuth setup")
    
    return True

if __name__ == "__main__":
    # Add the current directory to Python path
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    
    success = test_youtube_credentials()
    sys.exit(0 if success else 1)
