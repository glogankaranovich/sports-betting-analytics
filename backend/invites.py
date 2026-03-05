"""
Invite code management for invite-only signups
"""
import os
import secrets
from datetime import datetime, timezone
from typing import Optional, Dict
import boto3

dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.getenv('DYNAMODB_TABLE', 'carpool-bets-v2-dev')
table = dynamodb.Table(table_name)


def generate_invite_code(created_by: str, max_uses: int = 1, note: str = "") -> str:
    """Generate a new invite code"""
    code = secrets.token_urlsafe(12)
    
    table.put_item(Item={
        'pk': f'INVITE#{code}',
        'sk': 'METADATA',
        'code': code,
        'created_by': created_by,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'max_uses': max_uses,
        'used_count': 0,
        'note': note,
        'active': True
    })
    
    return code


def validate_invite_code(code: str) -> Dict:
    """Validate an invite code and return its details"""
    response = table.get_item(Key={'pk': f'INVITE#{code}', 'sk': 'METADATA'})
    
    if 'Item' not in response:
        return {'valid': False, 'reason': 'Invalid invite code'}
    
    invite = response['Item']
    
    if not invite.get('active', False):
        return {'valid': False, 'reason': 'Invite code has been deactivated'}
    
    if invite.get('used_count', 0) >= invite.get('max_uses', 1):
        return {'valid': False, 'reason': 'Invite code has reached maximum uses'}
    
    return {'valid': True, 'invite': invite}


def use_invite_code(code: str, used_by: str) -> bool:
    """Mark an invite code as used"""
    try:
        # Increment used_count
        table.update_item(
            Key={'pk': f'INVITE#{code}', 'sk': 'METADATA'},
            UpdateExpression='SET used_count = used_count + :inc, updated_at = :now',
            ExpressionAttributeValues={
                ':inc': 1,
                ':now': datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Record usage
        table.put_item(Item={
            'pk': f'INVITE#{code}',
            'sk': f'USED#{used_by}',
            'used_by': used_by,
            'used_at': datetime.now(timezone.utc).isoformat()
        })
        
        return True
    except Exception as e:
        print(f"Error using invite code: {e}")
        return False


def list_invite_codes(created_by: Optional[str] = None) -> list:
    """List all invite codes, optionally filtered by creator"""
    # This would need a GSI to be efficient
    # For now, return empty - implement when needed
    return []
