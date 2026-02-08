#!/bin/bash
# Update test user password to a strong password

USER_POOL_ID="us-east-1_UT5jyAP5L"
USERNAME="test@example.com"
PROFILE="sports-betting-dev"
REGION="us-east-1"

echo "🔐 Updating test user password..."
echo ""
echo "Enter new strong password (min 8 chars, uppercase, lowercase, number, special char):"
read -s NEW_PASSWORD

# Set permanent password
aws cognito-idp admin-set-user-password \
  --user-pool-id $USER_POOL_ID \
  --username $USERNAME \
  --password "$NEW_PASSWORD" \
  --permanent \
  --profile $PROFILE \
  --region $REGION

if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Password updated successfully!"
  echo ""
  echo "Test user credentials:"
  echo "  Email: $USERNAME"
  echo "  Password: [the one you just entered]"
  echo ""
  echo "⚠️  Save these credentials securely!"
else
  echo ""
  echo "❌ Failed to update password"
fi
