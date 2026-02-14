"""
User Subscriptions

Manages user subscription tiers and usage tracking.
"""

import os
from datetime import datetime
from typing import Optional

import boto3

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE", "carpool-bets-v2-dev"))


class UserSubscription:
    """User subscription management"""

    def __init__(
        self,
        user_id: str,
        tier: str,
        status: str = "active",
        stripe_subscription_id: str = None,
        current_period_start: str = None,
        current_period_end: str = None,
        api_calls_today: int = 0,
    ):
        self.user_id = user_id
        self.tier = tier
        self.status = status
        self.stripe_subscription_id = stripe_subscription_id
        self.current_period_start = current_period_start
        self.current_period_end = current_period_end
        self.api_calls_today = api_calls_today

    @staticmethod
    def get(user_id: str) -> Optional["UserSubscription"]:
        """Get user subscription"""
        try:
            response = table.get_item(
                Key={"pk": f"USER#{user_id}", "sk": "SUBSCRIPTION"}
            )
            if "Item" in response:
                item = response["Item"]
                return UserSubscription(
                    user_id=user_id,
                    tier=item.get("tier", "free"),
                    status=item.get("status", "active"),
                    stripe_subscription_id=item.get("stripe_subscription_id"),
                    current_period_start=item.get("current_period_start"),
                    current_period_end=item.get("current_period_end"),
                    api_calls_today=int(item.get("api_calls_today", 0)),
                )
            # Return free tier if no subscription found
            return UserSubscription(user_id=user_id, tier="free")
        except Exception as e:
            print(f"Error getting subscription: {e}")
            return UserSubscription(user_id=user_id, tier="free")

    def save(self):
        """Save subscription to DynamoDB"""
        table.put_item(
            Item={
                "pk": f"USER#{self.user_id}",
                "sk": "SUBSCRIPTION",
                "tier": self.tier,
                "status": self.status,
                "stripe_subscription_id": self.stripe_subscription_id,
                "current_period_start": self.current_period_start,
                "current_period_end": self.current_period_end,
                "api_calls_today": self.api_calls_today,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

    def increment_api_calls(self) -> bool:
        """Increment API call count, return False if limit exceeded"""
        from feature_flags import TIER_LIMITS, SubscriptionTier

        tier_enum = SubscriptionTier(self.tier)
        limits = TIER_LIMITS[tier_enum]
        daily_limit = limits["api_calls_per_day"]

        # Unlimited
        if daily_limit == -1:
            return True

        # Check limit
        if self.api_calls_today >= daily_limit:
            return False

        # Increment
        self.api_calls_today += 1
        self.save()
        return True

    def reset_daily_usage(self):
        """Reset daily API call counter (run daily via cron)"""
        self.api_calls_today = 0
        self.save()
