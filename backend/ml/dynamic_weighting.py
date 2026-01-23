"""Dynamic model weighting based on verified outcomes."""
import os
from datetime import datetime, timedelta
import boto3
from boto3.dynamodb.conditions import Key

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE", "sports-betting-bets-dev"))


class DynamicModelWeighting:
    """Adjust model confidence based on recent performance."""

    def __init__(self, lookback_days=30):
        self.lookback_days = lookback_days

    def get_recent_accuracy(self, model, sport, bet_type="game"):
        """Get recent accuracy for a model/sport/bet_type combination."""
        cutoff_date = (
            datetime.utcnow() - timedelta(days=self.lookback_days)
        ).isoformat()

        # Query verified analyses using GSI
        # PK: VERIFIED#{model}#{sport}#{bet_type}
        # SK: {verified_at}
        verified_pk = f"VERIFIED#{model}#{sport}#{bet_type}"

        response = table.query(
            IndexName="VerifiedAnalysisGSI",
            KeyConditionExpression=Key("verified_analysis_pk").eq(verified_pk)
            & Key("verified_analysis_sk").gte(cutoff_date),
        )

        analyses = response.get("Items", [])

        if not analyses:
            return None

        correct = sum(1 for a in analyses if a.get("analysis_correct"))
        return correct / len(analyses)

    def get_recent_brier_score(self, model, sport, bet_type="game"):
        """Calculate Brier score for recent predictions."""
        cutoff_date = (
            datetime.utcnow() - timedelta(days=self.lookback_days)
        ).isoformat()

        verified_pk = f"VERIFIED#{model}#{sport}#{bet_type}"

        response = table.query(
            IndexName="VerifiedAnalysisGSI",
            KeyConditionExpression=Key("verified_analysis_pk").eq(verified_pk)
            & Key("verified_analysis_sk").gte(cutoff_date),
        )

        analyses = response.get("Items", [])

        if not analyses:
            return None

        # Brier score: mean squared error of probability predictions
        brier_sum = 0
        for a in analyses:
            confidence = float(a.get("confidence", 0))
            actual = 1 if a.get("analysis_correct") else 0
            brier_sum += (confidence - actual) ** 2

        return brier_sum / len(analyses)

    def calculate_adjusted_confidence(
        self, base_confidence, model, sport, bet_type="game"
    ):
        """Adjust confidence based on recent model performance."""
        accuracy = self.get_recent_accuracy(model, sport, bet_type)

        # If no historical data, return base confidence
        if accuracy is None:
            return base_confidence

        # Boost confidence for models performing above 60%
        if accuracy > 0.6:
            multiplier = 1.0 + (accuracy - 0.6) * 0.5  # Up to 1.2x at 80%
        else:
            # Reduce confidence for underperforming models
            multiplier = accuracy / 0.6  # Down to 0.5x at 30%

        adjusted = base_confidence * multiplier
        return min(adjusted, 1.0)  # Cap at 1.0

    def get_model_weights(self, sport, bet_type="game", models=None):
        """Calculate dynamic weights for multiple models."""
        if models is None:
            models = ["consensus", "value", "momentum"]

        performances = {}
        for model in models:
            accuracy = self.get_recent_accuracy(model, sport, bet_type)
            brier_score = self.get_recent_brier_score(model, sport, bet_type)

            # If no data, use neutral weight
            if accuracy is None or brier_score is None:
                performances[model] = 0.5
            else:
                # Combined performance score (70% accuracy, 30% calibration)
                performances[model] = (accuracy * 0.7) + ((1 - brier_score) * 0.3)

        # Normalize to weights
        total = sum(performances.values())
        if total == 0:
            # Equal weights if no performance data
            return {m: 1.0 / len(models) for m in models}

        return {m: p / total for m, p in performances.items()}
