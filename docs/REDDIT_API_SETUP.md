# Reddit API Setup Guide

## Step 1: Register Reddit Application

1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app..." at the bottom
3. Fill in the form:
   - **Name**: `sports-betting-analytics`
   - **App type**: Select "script" (for application-only OAuth)
   - **Description**: `Sentiment analysis for sports betting analytics`
   - **About URL**: Leave blank
   - **Redirect URI**: `http://localhost:8080` (required but not used for script apps)
4. Click "create app"

## Step 2: Get Credentials

After creating the app, you'll see:
- **Client ID**: The string under "personal use script" (looks like: `abc123XYZ`)
- **Client Secret**: The string labeled "secret" (looks like: `xyz789ABC-def456GHI`)

## Step 3: Store in AWS Secrets Manager

Run these commands for each environment:

```bash
# Dev
AWS_PROFILE=sports-betting-dev aws secretsmanager create-secret \
  --name reddit-api-credentials \
  --description "Reddit API credentials for sentiment analysis" \
  --secret-string '{"client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET"}'

# Staging
AWS_PROFILE=sports-betting-staging aws secretsmanager create-secret \
  --name reddit-api-credentials \
  --description "Reddit API credentials for sentiment analysis" \
  --secret-string '{"client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET"}'

# Prod
AWS_PROFILE=sports-betting-prod aws secretsmanager create-secret \
  --name reddit-api-credentials \
  --description "Reddit API credentials for sentiment analysis" \
  --secret-string '{"client_id":"YOUR_CLIENT_ID","client_secret":"YOUR_CLIENT_SECRET"}'
```

## Step 4: Grant Lambda Access

The NewsCollectorsStack already includes Secrets Manager permissions, so no additional IAM changes needed.

## Notes

- Reddit's free tier allows 100 requests/minute per OAuth client
- Script apps can only access public data (perfect for our use case)
- No user interaction required - uses application-only OAuth2 grant
