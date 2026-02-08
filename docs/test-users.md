# Test User Credentials

**Strong Password (All Environments)**: CarpoolBets2026!Secure#

## Development Environment
- **Email**: testuser@example.com
- **User Pool ID**: us-east-1_UT5jyAP5L
- **Client ID**: 4qs12vau007oineekjldjkn6v0
- **AWS Profile**: sports-betting-dev

## Beta/Staging Environment
- **Email**: testuser@example.com
- **User Pool ID**: us-east-1_eXhfQ3HC3
- **Client ID**: 62nen1ftj2rk34t10eosvmimfc
- **AWS Profile**: sports-betting-staging

## Production Environment
- **Email**: testuser@example.com
- **User Pool ID**: us-east-1_zv3tZRTEo
- **Client ID**: 1j3hlk1pjl8bbr4kib889u1du9
- **AWS Profile**: sports-betting-prod
- **Note**: App access disabled in production (shows "Coming Soon" page)

## Usage
These test users can be used to:
1. Test the React frontend authentication in dev/beta
2. Get JWT tokens for API testing
3. Validate the integration tests with real authentication

## Security Note
- Strong password enforced across all environments
- Production app access locked down (only landing page accessible)
- Beta/staging requires authentication to access app
- Keep these credentials secure
