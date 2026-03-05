"""
Lambda function to generate invite codes
"""
import json
import os
from invites import generate_invite_code


def lambda_handler(event, context):
    """Generate invite codes for admins"""
    try:
        # Parse request
        body = json.loads(event.get('body', '{}'))
        
        # Get user from auth token (simplified - should validate admin)
        user_id = body.get('user_id')
        max_uses = body.get('max_uses', 1)
        note = body.get('note', '')
        count = body.get('count', 1)
        
        if not user_id:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'user_id required'})
            }
        
        # Generate codes
        codes = []
        for _ in range(count):
            code = generate_invite_code(user_id, max_uses, note)
            codes.append(code)
        
        return {
            'statusCode': 200,
            'headers': {
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type,Authorization',
            },
            'body': json.dumps({
                'codes': codes,
                'invite_url': f"{os.environ.get('FRONTEND_URL', 'https://carpoolbets.com')}/signup?invite={{code}}"
            })
        }
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': str(e)})
        }
