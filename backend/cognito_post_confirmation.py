"""
Cognito post-confirmation trigger to mark invite code as used
"""
import json
import os
from datetime import datetime, timezone
import boto3
from invites import use_invite_code

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.getenv('DYNAMODB_TABLE', 'carpool-bets-v2-dev')
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    """Mark invite code as used and create subscription after successful signup"""
    try:
        user_attributes = event['request']['userAttributes']
        invite_code = user_attributes.get('custom:invite_code')
        tier = user_attributes.get('custom:tier', 'free')
        user_id = event['userName']
        email = user_attributes.get('email')
        
        # Mark invite code as used
        if invite_code:
            use_invite_code(invite_code, user_id)
        
        # Create user profile
        table.put_item(Item={
            'pk': f'USER#{user_id}',
            'sk': 'PROFILE',
            'email': email,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'preferences': {}
        })
        
        # Create subscription (all free in beta, paid in prod)
        table.put_item(Item={
            'pk': f'USER#{user_id}',
            'sk': 'SUBSCRIPTION',
            'tier': tier,
            'status': 'active',
            'created_at': datetime.now(timezone.utc).isoformat()
        })
        
        return event
    except Exception as e:
        print(f"Error in post-confirmation: {e}")
        return event
