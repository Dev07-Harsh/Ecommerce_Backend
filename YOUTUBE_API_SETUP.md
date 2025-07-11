# YouTube API Setup Guide

## Overview
This guide will help you set up YouTube API credentials for the YouTube Live integration feature.

## Prerequisites
- Google Cloud Console access
- A YouTube channel for your platform (this will be used for all merchant streams)

## Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Click on the project dropdown at the top
3. Click "New Project"
4. Enter project name: "AOIN YouTube Integration" (or your preferred name)
5. Click "Create"

## Step 2: Enable YouTube Data API v3

1. In your Google Cloud project, go to **APIs & Services** > **Library**
2. Search for "YouTube Data API v3"
3. Click on it and press **Enable**

## Step 3: Create OAuth 2.0 Credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **"+ CREATE CREDENTIALS"** > **"OAuth 2.0 Client IDs"**
3. If prompted, configure the OAuth consent screen:
   - Choose **External** (unless you have Google Workspace)
   - Fill in the required fields:
     - App name: "AOIN Live Streaming"
     - User support email: Your email
     - Developer contact information: Your email
   - Click **Save and Continue**
   - Skip Scopes for now (click **Save and Continue**)
   - Skip Test users (click **Save and Continue**)

4. Back to creating OAuth client:
   - Application type: **Web application**
   - Name: "YouTube Live Integration"
   - Authorized redirect URIs: Add these URLs:
     - `http://localhost:5001/api/live-streams/admin/youtube/oauth/callback`
     - `http://127.0.0.1:5001/api/live-streams/admin/youtube/oauth/callback`
   - Click **Create**

5. **Copy the credentials**:
   - Client ID: Will look like `123456789-abc123def456.apps.googleusercontent.com`
   - Client Secret: Will look like `GOCSPX-abcdef123456`

## Step 4: Configure OAuth Consent Screen Scopes

1. Go back to **APIs & Services** > **OAuth consent screen**
2. Click **Edit App**
3. Go to **Scopes** tab
4. Click **Add or Remove Scopes**
5. Add these scopes:
   - `https://www.googleapis.com/auth/youtube`
   - `https://www.googleapis.com/auth/youtube.force-ssl`
6. Click **Update** and **Save and Continue**

## Step 5: Update Environment Variables

Replace the placeholder values in your `.env` files:

### Backend (.env in Ecommerce_Backend folder):
```env
YOUTUBE_CLIENT_ID=your_actual_client_id_here
YOUTUBE_CLIENT_SECRET=your_actual_client_secret_here
YOUTUBE_REDIRECT_URI=http://localhost:5001/api/live-streams/admin/youtube/oauth/callback
```

### Frontend (.env in Ecommerce folder):
```env
YOUTUBE_CLIENT_ID=your_actual_client_id_here
YOUTUBE_CLIENT_SECRET=your_actual_client_secret_here
```

## Step 6: Test the Setup

1. Restart your live streaming server:
   ```bash
   cd d:\Ecommerce\Ecommerce_Backend
   python live_streaming_server/app.py
   ```

2. Go to SuperAdmin dashboard in your frontend
3. Navigate to **YouTube Integration** section
4. Click **Configure YouTube**
5. You should be redirected to Google OAuth flow

## Step 7: Complete OAuth Flow

1. Sign in with the Google account that owns your YouTube channel
2. Grant the required permissions
3. You'll be redirected back to the success page
4. The integration should now show as "Active"

## Troubleshooting

### Error 401: invalid_client
- Double-check that your Client ID and Client Secret are correct
- Ensure there are no extra spaces or characters
- Verify the redirect URI matches exactly

### Error 400: redirect_uri_mismatch
- Check that the redirect URI in Google Cloud Console matches: `http://localhost:5001/api/live-streams/admin/youtube/oauth/callback`
- Make sure the live streaming server is running on port 5001

### Error 403: access_denied
- The OAuth consent screen might need verification
- For testing, you can add your email to the test users list

### Quota Errors
- YouTube API has daily quotas (10,000 units by default)
- Creating a live broadcast costs ~50 units
- Monitor usage in Google Cloud Console

## Security Notes

1. **Keep credentials secure**: Never commit actual credentials to version control
2. **Use environment variables**: Always store credentials in `.env` files
3. **Platform account**: Use a dedicated Google account for your platform, not personal accounts
4. **Scopes**: Only request the minimum required scopes

## API Quotas and Limits

- **Daily quota**: 10,000 units (default)
- **Live broadcast creation**: ~50 units per broadcast
- **Channel info retrieval**: ~1 unit
- **Token refresh**: 0 units

You can request quota increases in Google Cloud Console if needed.

## Production Deployment

When deploying to production:

1. Update redirect URIs in Google Cloud Console to include your production domain
2. Update environment variables with production URLs
3. Consider using Google Cloud Secret Manager for credential storage
4. Set up monitoring for quota usage

## Example Working Configuration

Here's what your final configuration should look like:

```env
# Backend .env
YOUTUBE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=GOCSPX-abc123def456
YOUTUBE_REDIRECT_URI=http://localhost:5001/api/live-streams/admin/youtube/oauth/callback
```

After setup, merchants will be able to create live streams that automatically create corresponding YouTube Live events on your platform's channel.
