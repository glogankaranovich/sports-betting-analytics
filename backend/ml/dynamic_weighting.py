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

    def get_recent_accuracy(self, model, sport, bet_type="game", inverse=False):
        """Get recent accuracy for a model/sport/bet_type combination."""
        cutoff_date = (
            datetime.utcnow() - timedelta(days=self.lookback_days)
        ).isoformat()

        # Query verified analyses using GSI
        # PK: VERIFIED#{model}#{sport}#{bet_type}[#inverse]
        # SK: {verified_at}
        verified_pk = f"VERIFIED#{model}#{sport}#{bet_type}"
        if inverse:
            verified_pk += "#inverse"

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
        # Try to get cached adjustment first (more efficient)
        cached = self._get_cached_adjustment(model, sport, bet_type)
        if cached and "confidence_multiplier" in cached:
            multiplier = float(cached["confidence_multiplier"])
            adjusted = base_confidence * multiplier
            return min(adjusted, 1.0)

        # Fall back to calculating from scratch
        accuracy = self.get_recent_accuracy(model, sport, bet_type)
        inverse_accuracy = self.get_recent_accuracy(
            model, sport, bet_type, inverse=True
        )

        # If no historical data, return base confidence
        if accuracy is None:
            return base_confidence

        # Check if inverse performs better
        if inverse_accuracy and inverse_accuracy > accuracy and inverse_accuracy > 0.5:
            # Model should be inverted - reduce confidence significantly
            multiplier = 0.3  # Heavily penalize models that should be inverted
            print(
                f"WARNING: {model} inverse accuracy ({inverse_accuracy:.2%}) > original ({accuracy:.2%}) - reducing confidence"
            )
        elif accuracy < 0.5:
            # Underperforming model - reduce confidence
            multiplier = accuracy  # Direct scaling (40% accuracy = 0.4x multiplier)
        elif accuracy > 0.6:
            # Boost confidence for models performing above 60%
            multiplier = 1.0 + (accuracy - 0.6) * 0.5  # Up to 1.2x at 80%
        else:
            # Neutral performance (50-60%) - slight reduction
            multiplier = 0.8 + (accuracy - 0.5) * 2  # 0.8x to 1.0x

        adjusted = base_confidence * multiplier
        return min(adjusted, 1.0)  # Cap at 1.0

    def _get_cached_adjustment(self, model, sport, bet_type="game"):
        """Get cached adjustment from DynamoDB if available and recent."""
        try:
            response = table.get_item(
                Key={
                    "pk": f"MODEL_ADJUSTMENT#{sport}#{bet_type}",
                    "sk": model,
                }
            )

            if "Item" not in response:
                return None

            item = response["Item"]

            # Check if adjustment is recent (within 24 hours)
            updated_at = datetime.fromisoformat(item.get("updated_at", ""))
            age_hours = (datetime.utcnow() - updated_at).total_seconds() / 3600

            if age_hours > 24:
                return None  # Too old, recalculate

            return item

        except Exception as e:
            print(f"Error getting cached adjustment: {e}")
            return None

    def get_model_weights(self, sport, bet_type="game", models=None):
        """Calculate dynamic weights for multiple models."""
        if models is None:
            models = ["consensus", "value", "momentum"]

        performances = {}
        inversions = {}  # Track which models should be inverted
        
        for model in models:
            accuracy = self.get_recent_accuracy(model, sport, bet_type)
            inverse_accuracy = self.get_recent_accuracy(model, sport, bet_type, inverse=True)
            brier_score = self.get_recent_brier_score(model, sport, bet_type)

            # If no data, use neutral weight
            if accuracy is None or brier_score is None:
                performances[model] = 0.5
                inversions[model] = False
            else:
                # Use inverse accuracy if it's better
                if inverse_accuracy and inverse_accuracy > accuracy:
                    performances[model] = (inverse_accuracy * 0.7) + ((1 - brier_score) * 0.3)
                    inversions[model] = True
                else:
                    performances[model] = (accuracy * 0.7) + ((1 - brier_score) * 0.3)
                    inversions[model] = False

        # Normalize to weights
        total = sum(performances.values())
        if total == 0:
            # Equal weights if no performance data
            return {m: 1.0 / len(models) for m in models}, {m: False for m in models}

        weights = {m: p / total for m, p in performances.items()}
        return weights, inversions

    def get_model_recommendation(self, model, sport, bet_type="game"):
        """Get recommendation for a model: ORIGINAL, INVERSE, or AVOID."""
        accuracy = self.get_recent_accuracy(model, sport, bet_type)
        inverse_accuracy = self.get_recent_accuracy(
            model, sport, bet_type, inverse=True
        )

        if accuracy is None:
            return {
                "recommendation": "INSUFFICIENT_DATA",
                "original_accuracy": None,
                "inverse_accuracy": None,
                "sample_size": 0,
            }

        # Get sample size
        cutoff_date = (
            datetime.utcnow() - timedelta(days=self.lookback_days)
        ).isoformat()
        verified_pk = f"VERIFIED#{model}#{sport}#{bet_type}"
        response = table.query(
            IndexName="VerifiedAnalysisGSI",
            KeyConditionExpression=Key("verified_analysis_pk").eq(verified_pk)
            & Key("verified_analysis_sk").gte(cutoff_date),
        )
        sample_size = len(response.get("Items", []))

        # Determine recommendation
        if inverse_accuracy and inverse_accuracy > accuracy and inverse_accuracy > 0.5:
            recommendation = "INVERSE"
        elif accuracy > 0.5:
            recommendation = "ORIGINAL"
        else:
            recommendation = "AVOID"

        return {
            "recommendation": recommendation,
            "original_accuracy": accuracy,
            "inverse_accuracy": inverse_accuracy,
            "sample_size": sample_size,
            "confidence_multiplier": self._get_confidence_multiplier(
                accuracy, inverse_accuracy
            ),
        }

    def _get_confidence_multiplier(self, accuracy, inverse_accuracy):
        """Calculate confidence multiplier based on performance."""
        if inverse_accuracy and inverse_accuracy > accuracy and inverse_accuracy > 0.5:
            return 0.3  # Heavily penalize
        elif accuracy < 0.5:
            return accuracy  # Direct scaling
        elif accuracy > 0.6:
            return 1.0 + (accuracy - 0.6) * 0.5  # Boost
        else:
            return 0.8 + (accuracy - 0.5) * 2  # Slight reduction

    def store_model_adjustments(self, sport, bet_type="game"):
        """Store adjustment factors for all models in DynamoDB."""
        models = [
            "consensus",
            "value",
            "momentum",
            "contrarian",
            "hot_cold",
            "rest_schedule",
            "matchup",
            "injury_aware",
            "ensemble",
            "benny",
        ]

        adjustments = []
        for model in models:
            rec = self.get_model_recommendation(model, sport, bet_type)
            if rec["recommendation"] != "INSUFFICIENT_DATA":
                adjustments.append(
                    {
                        "model": model,
                        "sport": sport,
                        "bet_type": bet_type,
                        **rec,
                    }
                )

                # Store in DynamoDB
                table.put_item(
                    Item={
                        "pk": f"MODEL_ADJUSTMENT#{sport}#{bet_type}",
                        "sk": model,
                        "model": model,
                        "sport": sport,
                        "bet_type": bet_type,
                        "recommendation": rec["recommendation"],
                        "original_accuracy": rec["original_accuracy"],
                        "inverse_accuracy": rec["inverse_accuracy"] or 0,
                        "sample_size": rec["sample_size"],
                        "confidence_multiplier": rec["confidence_multiplier"],
                        "updated_at": datetime.utcnow().isoformat(),
                        "lookback_days": self.lookback_days,
                    }
                )

        return adjustments
