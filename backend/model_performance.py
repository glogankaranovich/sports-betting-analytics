"""
Model Performance Monitoring

Tracks prediction accuracy, confidence calibration, and ROI by model over time.
This data is used for dynamic model weighting and performance analysis.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

import boto3

logger = logging.getLogger(__name__)


class ModelPerformanceTracker:
    """Track and analyze model performance metrics"""

    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(table_name)

    def get_model_performance(
        self, model: str, sport: str, days: int = 30
    ) -> Dict[str, Any]:
        """
        Get performance metrics for a specific model

        Returns:
            {
                "total_predictions": int,
                "correct_predictions": int,
                "accuracy": float,
                "avg_confidence": float,
                "confidence_calibration": Dict[str, float],  # by confidence bucket
                "roi": float
            }
        """
        try:
            cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()

            # Query analyses with outcomes
            response = self.table.query(
                IndexName="AnalysisTimeGSI",
                KeyConditionExpression="begins_with(analysis_time_pk, :prefix) AND commence_time >= :cutoff",
                FilterExpression="attribute_exists(actual_outcome)",
                ExpressionAttributeValues={
                    ":prefix": f"ANALYSIS#{sport}#",
                    ":cutoff": cutoff_time,
                },
            )

            analyses = [
                item for item in response.get("Items", []) if item.get("model") == model
            ]

            if not analyses:
                return {
                    "total_predictions": 0,
                    "correct_predictions": 0,
                    "accuracy": 0.0,
                    "avg_confidence": 0.0,
                    "confidence_calibration": {},
                    "roi": 0.0,
                }

            # Calculate metrics
            total = len(analyses)
            correct = sum(1 for a in analyses if self._is_prediction_correct(a))
            accuracy = correct / total if total > 0 else 0.0

            confidences = [float(a.get("confidence", 0)) for a in analyses]
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0

            # Confidence calibration by bucket
            calibration = self._calculate_calibration(analyses)

            # ROI calculation (simplified - assumes $100 bet per prediction)
            roi = self._calculate_roi(analyses)

            return {
                "total_predictions": total,
                "correct_predictions": correct,
                "accuracy": accuracy,
                "avg_confidence": avg_confidence,
                "confidence_calibration": calibration,
                "roi": roi,
            }

        except Exception as e:
            logger.error(f"Error getting model performance: {e}", exc_info=True)
            return {
                "total_predictions": 0,
                "correct_predictions": 0,
                "accuracy": 0.0,
                "avg_confidence": 0.0,
                "confidence_calibration": {},
                "roi": 0.0,
            }

    def _is_prediction_correct(self, analysis: Dict[str, Any]) -> bool:
        """Check if prediction matches actual outcome"""
        prediction = analysis.get("prediction", "").lower()
        actual = analysis.get("actual_outcome", "").lower()

        if not prediction or not actual:
            return False

        # For game predictions
        if "home" in prediction and "home" in actual:
            return True
        if "away" in prediction and "away" in actual:
            return True

        # For prop predictions (Over/Under)
        if "over" in prediction and "over" in actual:
            return True
        if "under" in prediction and "under" in actual:
            return True

        return False

    def _calculate_calibration(
        self, analyses: List[Dict[str, Any]]
    ) -> Dict[str, float]:
        """Calculate confidence calibration by bucket"""
        buckets = {
            "0.5-0.6": [],
            "0.6-0.7": [],
            "0.7-0.8": [],
            "0.8-0.9": [],
            "0.9-1.0": [],
        }

        for analysis in analyses:
            confidence = float(analysis.get("confidence", 0))
            correct = self._is_prediction_correct(analysis)

            if 0.5 <= confidence < 0.6:
                buckets["0.5-0.6"].append(correct)
            elif 0.6 <= confidence < 0.7:
                buckets["0.6-0.7"].append(correct)
            elif 0.7 <= confidence < 0.8:
                buckets["0.7-0.8"].append(correct)
            elif 0.8 <= confidence < 0.9:
                buckets["0.8-0.9"].append(correct)
            elif 0.9 <= confidence <= 1.0:
                buckets["0.9-1.0"].append(correct)

        # Calculate accuracy per bucket
        calibration = {}
        for bucket, results in buckets.items():
            if results:
                calibration[bucket] = sum(results) / len(results)

        return calibration

    def _calculate_roi(self, analyses: List[Dict[str, Any]]) -> float:
        """Calculate ROI assuming $100 bet per prediction"""
        total_bet = len(analyses) * 100
        total_return = 0

        for analysis in analyses:
            if self._is_prediction_correct(analysis):
                # Simplified: assume -110 odds (bet $110 to win $100)
                total_return += 100 + (100 / 1.1)

        profit = total_return - total_bet
        roi = (profit / total_bet) if total_bet > 0 else 0.0

        return roi

    def get_all_models_performance(
        self, sport: str, days: int = 30
    ) -> Dict[str, Dict[str, Any]]:
        """Get performance metrics for all models"""
        models = [
            "consensus",
            "value",
            "momentum",
            "contrarian",
            "hot_cold",
            "rest_schedule",
            "matchup",
            "injury_aware",
        ]

        performance = {}
        for model in models:
            performance[model] = self.get_model_performance(model, sport, days)

        return performance
