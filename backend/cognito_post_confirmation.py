"""
Cognito post-confirmation trigger to mark invite code as used
"""
import json
from invites import use_invite_code


def lambda_handler(event, context):
    """Mark invite code as used after successful signup"""
    try:
        user_attributes = event['request']['userAttributes']
        invite_code = user_attributes.get('custom:invite_code')
        user_id = event['userName']
        
        if invite_code:
            use_invite_code(invite_code, user_id)
        
        return event
    except Exception as e:
        print(f"Error in post-confirmation: {e}")
        return event
