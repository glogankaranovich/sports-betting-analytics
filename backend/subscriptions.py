"""
User Subscriptions

Manages user subscription tiers.
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
    ):
        self.user_id = user_id
        self.tier = tier
        self.status = status
        self.stripe_subscription_id = stripe_subscription_id
        self.current_period_start = current_period_start
        self.current_period_end = current_period_end

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
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

    def update_tier(self, new_tier: str, stripe_subscription_id: str = None):
        """Update subscription tier"""
        self.tier = new_tier
        if stripe_subscription_id:
            self.stripe_subscription_id = stripe_subscription_id
        self.save()

    def cancel(self):
        """Cancel subscription (downgrade to free)"""
        self.tier = "free"
        self.status = "cancelled"
        self.save()
