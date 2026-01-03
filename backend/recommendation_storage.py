import boto3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from bet_recommendations import BetRecommendation, RiskLevel


class RecommendationStorage:
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.table = self.dynamodb.Table(table_name)

    def store_recommendations(
        self,
        sport: str,
        model: str,
        risk_level: RiskLevel,
        recommendations: List[BetRecommendation],
    ) -> None:
        """Store top 10 recommendations for a sport/model/risk combination"""
        pk = f"RECOMMENDATIONS#{sport}#{model}#{risk_level.value}"
        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")

        # Clear existing recommendations for this combination
        self._clear_existing_recommendations(pk)

        # Store new recommendations
        for i, rec in enumerate(recommendations[:10], 1):
            sk = f"REC#{i:02d}#{timestamp}#{rec.game_id}"

            item = {
                "PK": pk,
                "SK": sk,
                "prediction_pk": f"GAME#{rec.game_id}",
                "prediction_sk": f"PREDICTION#{model}",
                "rank": i,
                "sport": sport,
                "game_id": rec.game_id,
                "model": model,
                "risk_level": risk_level.value,
                "bet_type": rec.bet_type,
                "team_or_player": rec.team_or_player,
                "market": rec.market,
                "predicted_probability": Decimal(str(rec.predicted_probability)),
                "confidence_score": Decimal(str(rec.confidence_score)),
                "expected_value": Decimal(str(rec.expected_value)),
                "recommended_bet_amount": Decimal(str(rec.recommended_bet_amount)),
                "potential_payout": Decimal(str(rec.potential_payout)),
                "bookmaker": rec.bookmaker,
                "odds": Decimal(str(rec.odds)),
                "reasoning": rec.reasoning,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "is_active": True,
                "actual_outcome": None,
                "bet_won": None,
                "actual_roi": None,
                "outcome_verified_at": None,
            }

            self.table.put_item(Item=item)

    def get_recommendations(
        self, sport: str, model: str, risk_level: RiskLevel, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get stored recommendations for a sport/model/risk combination"""
        pk = f"RECOMMENDATIONS#{sport}#{model}#{risk_level.value}"

        response = self.table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": pk},
            Limit=limit,
            ScanIndexForward=True,
        )

        return response.get("Items", [])

    def _clear_existing_recommendations(self, pk: str) -> None:
        """Clear existing recommendations for a PK"""
        response = self.table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": pk},
            ProjectionExpression="PK, SK",
        )

        for item in response.get("Items", []):
            self.table.delete_item(Key={"PK": item["PK"], "SK": item["SK"]})

    def update_recommendation_outcome(
        self, pk: str, sk: str, outcome: bool, roi: float
    ) -> None:
        """Update recommendation with actual outcome"""
        self.table.update_item(
            Key={"PK": pk, "SK": sk},
            UpdateExpression="SET actual_outcome = :outcome, bet_won = :won, actual_roi = :roi, outcome_verified_at = :verified",
            ExpressionAttributeValues={
                ":outcome": outcome,
                ":won": outcome,
                ":roi": Decimal(str(roi)),
                ":verified": datetime.utcnow().isoformat(),
            },
        )
