# YouTube Live Integration Documentation

## Overview

This implementation adds YouTube Live streaming integration to the live_streaming_server module. When merchants schedule live streams, corresponding YouTube Live events are automatically created on the platform's YouTube channel.

## Features

### 1. **SuperAdmin YouTube Configuration**
- One-time OAuth setup for platform's YouTube channel
- Token management with expiry notifications
- Database storage of access and refresh tokens
- Token auto-refresh functionality

### 2. **Automatic YouTube Event Creation**
- When merchants schedule streams, YouTube events are created automatically
- Graceful fallback: streams work even if YouTube fails
- YouTube event details stored in stream records

### 3. **Dashboard Integration**
- SuperAdmin dashboard shows YouTube integration status
- Notifications for token expiry (7+ days before expiration)
- Easy token renewal process

## Database Schema Changes

### New Table: `youtube_tokens`
```sql
CREATE TABLE youtube_tokens (
    id INT PRIMARY KEY AUTO_INCREMENT,
    access_token TEXT NOT NULL,
    refresh_token TEXT NOT NULL,
    token_type VARCHAR(50) DEFAULT 'Bearer',
    expires_at DATETIME NOT NULL,
    created_by INT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

### Updated Table: `live_streams`
New columns added:
- `youtube_event_id` VARCHAR(255) - YouTube broadcast ID
- `youtube_broadcast_url` VARCHAR(500) - YouTube watch URL
- `youtube_stream_url` VARCHAR(500) - YouTube embed URL

## API Endpoints

### SuperAdmin YouTube OAuth

#### 1. Initiate OAuth Flow
**POST** `/api/live-streams/admin/youtube/oauth/initiate`
- **Auth**: SuperAdmin required
- **Response**: Authorization URL for YouTube OAuth

#### 2. OAuth Callback
**GET** `/api/live-streams/admin/youtube/oauth/callback`
- **Auth**: None (OAuth callback)
- **Response**: Success page with token details

#### 3. Get YouTube Status
**GET** `/api/live-streams/admin/youtube/status`
- **Auth**: SuperAdmin required
- **Response**: Current token status and expiry info

#### 4. Refresh Token
**POST** `/api/live-streams/admin/youtube/token/refresh`
- **Auth**: SuperAdmin required
- **Response**: Token refresh status

#### 5. Revoke Token
**DELETE** `/api/live-streams/admin/youtube/token/revoke`
- **Auth**: SuperAdmin required
- **Response**: Token revocation confirmation

### SuperAdmin Dashboard Integration

#### 1. Dashboard Status
**GET** `/api/superadmin/youtube/status`
- **Auth**: SuperAdmin required
- **Response**: Dashboard data with notifications and required actions

#### 2. Configure Integration
**POST** `/api/superadmin/youtube/configure`
- **Auth**: SuperAdmin required
- **Response**: OAuth URL and setup instructions

#### 3. Test Connection
**POST** `/api/superadmin/youtube/test-connection`
- **Auth**: SuperAdmin required
- **Response**: Connection test results and channel info

#### 4. Integration Statistics
**GET** `/api/superadmin/youtube/stats`
- **Auth**: SuperAdmin required
- **Response**: Usage statistics and success rates

## Configuration

### Environment Variables
Add these to your `.env` file:

```env
# YouTube API Configuration
YOUTUBE_CLIENT_ID=your_youtube_client_id
YOUTUBE_CLIENT_SECRET=your_youtube_client_secret
YOUTUBE_REDIRECT_URI=http://localhost:5001/api/live-streams/admin/youtube/oauth/callback
```

### YouTube API Setup

1. **Create Google Cloud Project**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select existing one

2. **Enable YouTube Data API**
   - Navigate to APIs & Services > Library
   - Search for "YouTube Data API v3"
   - Enable the API

3. **Create OAuth Credentials**
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Application type: Web application
   - Add redirect URI: `http://localhost:5001/api/live-streams/admin/youtube/oauth/callback`

4. **Configure OAuth Consent Screen**
   - Set up the consent screen with your app details
   - Add required scopes:
     - `https://www.googleapis.com/auth/youtube`
     - `https://www.googleapis.com/auth/youtube.force-ssl`

## Usage Flow

### Initial Setup (SuperAdmin)

1. **Configure YouTube Integration**
   ```bash
   GET /api/superadmin/youtube/status
   # Check current status
   
   POST /api/superadmin/youtube/configure
   # Get OAuth URL
   ```

2. **Complete OAuth Flow**
   - Visit the OAuth URL from step 1
   - Sign in with platform's YouTube account
   - Grant permissions
   - Automatically redirected to callback

3. **Verify Setup**
   ```bash
   POST /api/superadmin/youtube/test-connection
   # Test API connection and get channel info
   ```

### Daily Operations (Automatic)

1. **Merchant Creates Stream**
   ```bash
   POST /api/live-streams/
   {
     "title": "Product Demo Stream",
     "description": "Live demo of our new product",
     "product_id": 123,
     "scheduled_time": "2024-01-15T15:00:00Z"
   }
   ```

2. **Response Includes YouTube Info**
   ```json
   {
     "success": true,
     "data": {
       "stream_id": 456,
       "title": "Product Demo Stream",
       "youtube_event_id": "abc123xyz",
       "youtube_broadcast_url": "https://www.youtube.com/watch?v=abc123xyz",
       "youtube_stream_url": "https://www.youtube.com/embed/abc123xyz",
       "youtube_integration": {
         "status": "success",
         "broadcast_id": "abc123xyz",
         "watch_url": "https://www.youtube.com/watch?v=abc123xyz"
       }
     }
   }
   ```

### Token Management

The system automatically:
- Refreshes tokens when they're about to expire (within 1 hour)
- Notifies SuperAdmin when tokens expire within 7 days
- Handles token expiry gracefully (streams still work without YouTube)

## Error Handling

### Graceful Degradation
- If YouTube API fails, stream creation continues normally
- Error logged but doesn't break the core functionality
- Response indicates YouTube integration status

### Common Error Scenarios

1. **No YouTube Token**
   ```json
   {
     "youtube_integration": {
       "status": "failed",
       "message": "YouTube integration not configured"
     }
   }
   ```

2. **Expired Token**
   ```json
   {
     "youtube_integration": {
       "status": "failed",
       "message": "YouTube token expired. Please renew."
     }
   }
   ```

3. **API Quota Exceeded**
   ```json
   {
     "youtube_integration": {
       "status": "failed",
       "message": "YouTube API quota exceeded. Try again later."
     }
   }
   ```

## Monitoring and Notifications

### Dashboard Notifications

The SuperAdmin dashboard shows:

1. **Warning Notifications**
   - Token expires in 7+ days
   - Integration not configured

2. **Error Notifications**
   - Token expired
   - API connection failed

3. **Success Statistics**
   - Total streams with YouTube integration
   - Success rate percentage
   - Recent integration activity

### Log Monitoring

Check logs for:
- `INFO: YouTube Live event created successfully`
- `WARNING: Failed to create YouTube event`
- `ERROR: YouTube API error`

## Security Considerations

1. **Token Storage**
   - Tokens stored encrypted in database
   - Only SuperAdmin can access token management
   - Automatic token refresh prevents long-term storage of expired tokens

2. **OAuth Scope**
   - Minimal required scopes for YouTube API
   - Platform account used (not individual merchants)

3. **Error Information**
   - Sensitive API errors not exposed to merchants
   - Detailed errors only in server logs

## Troubleshooting

### Common Issues

1. **"No module named 'google'" Error**
   ```bash
   pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
   ```

2. **OAuth Redirect URI Mismatch**
   - Check Google Cloud Console redirect URIs
   - Ensure `YOUTUBE_REDIRECT_URI` matches exactly

3. **Token Refresh Failures**
   - Re-run OAuth flow to get new refresh token
   - Check if YouTube API quotas are exceeded

4. **Database Connection Issues**
   ```bash
   # Recreate tables if needed
   python -c "
   from flask import Flask
   from config import get_config
   from common.database import db
   from models.youtube_token import YouTubeToken
   
   app = Flask(__name__)
   app.config.from_object(get_config())
   db.init_app(app)
   
   with app.app_context():
       db.create_all()
   "
   ```

## Testing

### Manual Testing

1. **Test OAuth Flow**
   - Access `/api/live-streams/admin/youtube/oauth/initiate`
   - Complete OAuth process
   - Verify token storage

2. **Test Stream Creation**
   - Create a live stream as merchant
   - Check YouTube event creation
   - Verify database updates

3. **Test Token Refresh**
   - Manually trigger refresh
   - Check token update in database

### Integration Testing

```python
# Test YouTube service
from live_streaming_server.services.youtube_live_service import YouTubeLiveService

service = YouTubeLiveService()
status = service.get_token_status()
print(f"Token status: {status}")

# Test stream creation with YouTube
from datetime import datetime, timedelta
future_time = datetime.utcnow() + timedelta(hours=2)

youtube_event = service.create_youtube_live_event(
    title="Test Stream",
    description="Test Description", 
    scheduled_time=future_time
)
print(f"YouTube event: {youtube_event}")
```

## Dependencies

### Added Packages
```txt
google-api-python-client==2.108.0
google-auth-oauthlib==1.1.0
google-auth-httplib2==0.1.1
```

### Import Requirements
```python
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
```

## Performance Considerations

1. **YouTube API Quotas**
   - 10,000 units per day (default)
   - Creating a broadcast: ~50 units
   - Monitor usage in Google Cloud Console

2. **Token Refresh**
   - Automatic refresh when needed
   - Cached credentials to avoid repeated API calls

3. **Error Caching**
   - Failed YouTube requests don't retry immediately
   - Graceful degradation ensures stream creation speed

## Future Enhancements

1. **Merchant-Level YouTube Integration**
   - Allow merchants to connect their own channels
   - Multiple YouTube accounts support

2. **Live Stream Analytics**
   - YouTube viewer statistics integration
   - Performance metrics from YouTube API

3. **Advanced Scheduling**
   - Bulk YouTube event creation
   - Template-based event creation

4. **Webhook Integration**
   - YouTube event status updates
   - Real-time synchronization

This completes the YouTube Live integration implementation for the live_streaming_server module.
