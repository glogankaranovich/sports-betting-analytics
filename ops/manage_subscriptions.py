#!/usr/bin/env python3
"""
Manage user subscriptions.
Usage: AWS_PROFILE=sports-betting-staging python3 manage_subscriptions.py --email <email> --tier <tier>
       AWS_PROFILE=sports-betting-staging python3 manage_subscriptions.py --user-id <uuid> --tier <tier>
"""
import argparse
import sys
import os
import boto3

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from subscriptions import UserSubscription
from feature_flags import SubscriptionTier

# Cognito user pool IDs by environment
USER_POOLS = {
    'dev': 'us-east-1_UT5jyAP5L',
    'staging': 'us-east-1_eXhfQ3HC3',
    'beta': 'us-east-1_eXhfQ3HC3',
    'prod': 'us-east-1_zv3tZRTEo'
}


def get_user_id_from_email(email: str, env: str = 'beta') -> str:
    """Get Cognito UUID from email"""
    cognito = boto3.client('cognito-idp')
    user_pool_id = USER_POOLS.get(env)
    
    try:
        response = cognito.admin_get_user(
            UserPoolId=user_pool_id,
            Username=email
        )
        for attr in response['UserAttributes']:
            if attr['Name'] == 'sub':
                return attr['Value']
    except Exception as e:
        print(f"❌ Error looking up user: {e}")
        return None


def set_user_tier(user_id: str, tier: str):
    """Set user subscription tier"""
    try:
        tier_enum = SubscriptionTier(tier)
    except ValueError:
        print(f"❌ Invalid tier: {tier}")
        print(f"Valid tiers: {', '.join([t.value for t in SubscriptionTier])}")
        return False
    
    subscription = UserSubscription.get(user_id)
    subscription.update_tier(tier)
    
    print(f"✓ Updated {user_id} to {tier} tier")
    return True


def get_user_subscription(user_id: str):
    """Get user subscription details"""
    subscription = UserSubscription.get(user_id)
    
    print(f"\n{'='*60}")
    print(f"User: {user_id}")
    print(f"{'='*60}")
    print(f"Tier:   {subscription.tier}")
    print(f"Status: {subscription.status}")
    if subscription.stripe_subscription_id:
        print(f"Stripe: {subscription.stripe_subscription_id}")
    print(f"{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description='Manage user subscriptions')
    parser.add_argument('--user-id', help='User ID (Cognito UUID)')
    parser.add_argument('--email', help='User email (will lookup UUID)')
    parser.add_argument('--tier', choices=['free', 'basic', 'pro'],
                        help='Set subscription tier')
    parser.add_argument('--show', action='store_true',
                        help='Show current subscription')
    parser.add_argument('--env', default='beta', choices=['dev', 'staging', 'beta', 'prod'],
                        help='Environment (default: beta)')
    
    args = parser.parse_args()
    
    if not args.user_id and not args.email:
        parser.error('Either --user-id or --email is required')
    
    user_id = args.user_id
    if args.email:
        user_id = get_user_id_from_email(args.email, args.env)
        if not user_id:
            return
        print(f"Found user: {user_id}")
    
    if args.tier:
        set_user_tier(user_id, args.tier)
    
    if args.show or not args.tier:
        get_user_subscription(user_id)


if __name__ == '__main__':
    main()
