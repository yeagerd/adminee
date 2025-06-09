# Office Service Live Demo

This demo shows how to use the Office Service with real API credentials to fetch emails, calendar events, and files from Google and Microsoft, **without requiring the user management service**.

## How it Works

The demo bypasses the normal token management service by:
1. Reading API tokens directly from environment variables
2. Creating API clients directly with those tokens
3. Using the Office Service's core functionality (clients + normalizers) to fetch and unify data

## Setup Instructions

### 1. Get Google API Token (Optional)

To access Gmail, Google Calendar, and Google Drive:

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Gmail API, Calendar API, and Drive API
4. Create OAuth 2.0 credentials:
   - Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client ID"
   - Choose "Desktop application" or "Web application"
   - Download the client configuration JSON
5. Use the OAuth 2.0 Playground or a simple script to get an access token:
   - Go to [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)
   - Click the gear icon and check "Use your own OAuth credentials"
   - Enter your Client ID and Client Secret
   - Select the required scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/calendar.readonly`
     - `https://www.googleapis.com/auth/drive.readonly`
   - Follow the flow to get your access token

### 2. Get Microsoft API Token (Optional)

To access Outlook, Microsoft Calendar, and OneDrive:

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application:
   - Go to "Azure Active Directory" → "App registrations" → "New registration"
   - Choose "Accounts in any organizational directory and personal Microsoft accounts"
3. Add API permissions:
   - Go to "API permissions" → "Add a permission" → "Microsoft Graph"
   - Add these delegated permissions:
     - `Mail.Read`
     - `Calendars.Read`
     - `Files.Read`
4. Get an access token:
   - Use the Microsoft Graph Explorer: https://developer.microsoft.com/en-us/graph/graph-explorer
   - Sign in and copy the access token from the "Access Token" tab
   - Or use the OAuth 2.0 flow with your app registration

### 3. Set Environment Variables

```bash
# For Google services (optional)
export GOOGLE_ACCESS_TOKEN="your-google-oauth-token-here"

# For Microsoft services (optional)
export MICROSOFT_ACCESS_TOKEN="your-microsoft-graph-token-here"
```

You can set one or both tokens depending on which services you want to test.

### 4. Run the Demo

```bash
# From the repository root
cd /path/to/briefly
python services/demos/office.py
```

## What the Demo Does

The demo will:

1. **Fetch Emails**: Get the latest emails from Gmail and/or Outlook
2. **Fetch Calendar Events**: Get upcoming calendar events from Google Calendar and/or Outlook Calendar
3. **Fetch Files**: Get recent files from Google Drive and/or OneDrive
4. **Display Results**: Show a unified summary of all fetched data

## Sample Output

```
🚀 Office Service Live Demo
==================================================
🔑 Available providers: Google (Gmail, Calendar, Drive), Microsoft (Outlook, Calendar, OneDrive)

==================================================
 FETCHING EMAILS
==================================================
📧 Fetching emails from Gmail...
✅ Found 3 Gmail messages
📧 Fetching emails from Outlook...
✅ Found 3 Outlook messages

==================================================
 📧 EMAIL SUMMARY
==================================================

GOOGLE (3 messages):
  1. From: sender@example.com
     Subject: Important Meeting Tomorrow
     Date: 2024-01-15 14:30
     Preview: Hi, just wanted to remind you about our meeting tomorrow at...

MICROSOFT (3 messages):
  1. From: colleague@company.com
     Subject: Project Update
     Date: 2024-01-15 09:15
     Preview: Here's the latest update on the project we discussed...

==================================================
 ✅ DEMO COMPLETE
==================================================
Successfully fetched:
  📧 6 emails
  📅 4 calendar events
  📁 8 files

The Office Service unified API is working! 🎉
```

## Important Notes

- **Token Expiration**: Access tokens typically expire after 1 hour. You'll need to refresh them or get new ones.
- **Scopes**: Make sure your tokens have the necessary scopes for the data you want to access.
- **Rate Limits**: The demo respects API rate limits but doesn't implement sophisticated retry logic.
- **Production Use**: For production, you'd use the full Office Service with proper token management and refresh logic.

## Troubleshooting

### "No API tokens found!"
- Make sure you've set the environment variables correctly
- Check that the token values don't have extra quotes or spaces

### Authentication errors
- Your token may have expired (common after 1 hour)
- Check that your token has the required scopes
- For Google: ensure the APIs are enabled in Google Cloud Console
- For Microsoft: ensure the app has the required permissions in Azure Portal

### Import errors
- Make sure you're running from the repository root directory
- The Office Service code should be in `services/office_service/` 