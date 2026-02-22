"""
Market Inefficiency Tracker

Tracks when models strongly disagree with market odds and whether those
disagreements are profitable over time.
"""
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List

import boto3


class MarketInefficiencyTracker:
    """Track model vs market disagreements and their profitability"""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def log_disagreement(
        self,
        game_id: str,
        model: str,
        sport: str,
        model_prediction: str,
        model_spread: float,
        market_spread: float,
        confidence: float,
    ):
        """Log when model disagrees with market"""
        disagreement = abs(model_spread - market_spread)

        # Only log significant disagreements
        if disagreement < 1.0:
            return

        pk = f"INEFFICIENCY#{sport}#{model}"
        sk = f"{game_id}#{datetime.utcnow().isoformat()}"

        self.table.put_item(
            Item={
                "pk": pk,
                "sk": sk,
                "game_id": game_id,
                "model": model,
                "sport": sport,
                "model_prediction": model_prediction,
                "model_spread": model_spread,
                "market_spread": market_spread,
                "disagreement": disagreement,
                "confidence": confidence,
                "logged_at": datetime.utcnow().isoformat(),
            }
        )

    def get_profitable_disagreements(
        self, model: str, sport: str, days: int = 30
    ) -> Dict[str, Any]:
        """Get stats on which disagreements were profitable"""
        cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()

        pk = f"INEFFICIENCY#{sport}#{model}"

        response = self.table.query(
            KeyConditionExpression="pk = :pk AND sk >= :cutoff",
            ExpressionAttributeValues={":pk": pk, ":cutoff": cutoff_time},
        )

        items = response.get("Items", [])

        if not items:
            return {
                "total_disagreements": 0,
                "profitable_count": 0,
                "profitability_rate": 0.0,
                "avg_disagreement": 0.0,
            }

        # Filter for items with outcomes
        with_outcomes = [item for item in items if "was_correct" in item]

        if not with_outcomes:
            return {
                "total_disagreements": len(items),
                "profitable_count": 0,
                "profitability_rate": 0.0,
                "avg_disagreement": sum(float(i.get("disagreement", 0)) for i in items)
                / len(items),
            }

        profitable = sum(1 for item in with_outcomes if item.get("was_correct"))

        return {
            "total_disagreements": len(with_outcomes),
            "profitable_count": profitable,
            "profitability_rate": profitable / len(with_outcomes),
            "avg_disagreement": sum(
                float(i.get("disagreement", 0)) for i in with_outcomes
            )
            / len(with_outcomes),
        }
