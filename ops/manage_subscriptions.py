#!/usr/bin/env python3
"""
Manage user subscriptions.
Usage: AWS_PROFILE=sports-betting-dev python3 manage_subscriptions.py --user-id <id> --tier <tier>
"""
import argparse
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from subscriptions import UserSubscription
from feature_flags import SubscriptionTier


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
    parser.add_argument('--user-id', required=True, help='User ID (email)')
    parser.add_argument('--tier', choices=['free', 'basic', 'pro'],
                        help='Set subscription tier')
    parser.add_argument('--show', action='store_true',
                        help='Show current subscription')
    
    args = parser.parse_args()
    
    if args.tier:
        set_user_tier(args.user_id, args.tier)
    
    if args.show or not args.tier:
        get_user_subscription(args.user_id)


if __name__ == '__main__':
    main()
