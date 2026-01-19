import boto3
import os
from typing import Dict, List, Any
from collections import defaultdict


class ModelAnalytics:
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.table = self.dynamodb.Table(table_name)

    def get_model_performance_summary(self) -> Dict[str, Dict[str, Any]]:
        """Get performance summary for each model"""
        predictions = self._get_verified_predictions()

        by_model = defaultdict(lambda: {"total": 0, "correct": 0, "sports": set()})

        for pred in predictions:
            model = pred.get("model", "unknown")
            by_model[model]["total"] += 1
            by_model[model]["sports"].add(pred.get("sport", "unknown"))

            if pred.get("prediction_correct", False):
                by_model[model]["correct"] += 1

        result = {}
        for model, stats in by_model.items():
            total = stats["total"]
            correct = stats["correct"]
            result[model] = {
                "model_name": model,
                "total_predictions": total,
                "correct_predictions": correct,
                "incorrect_predictions": total - correct,
                "accuracy": round((correct / total) * 100, 2) if total > 0 else 0.0,
                "sports_covered": list(stats["sports"]),
            }

        return result

    def get_model_performance_by_sport(
        self, model: str = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get model performance broken down by sport"""
        predictions = self._get_verified_predictions()

        # Filter by model if specified
        if model:
            predictions = [p for p in predictions if p.get("model") == model]

        by_model_sport = defaultdict(
            lambda: defaultdict(lambda: {"total": 0, "correct": 0})
        )

        for pred in predictions:
            model_name = pred.get("model", "unknown")
            sport = pred.get("sport", "unknown")

            by_model_sport[model_name][sport]["total"] += 1
            if pred.get("prediction_correct", False):
                by_model_sport[model_name][sport]["correct"] += 1

        result = {}
        for model_name, sports in by_model_sport.items():
            result[model_name] = {}
            for sport, stats in sports.items():
                total = stats["total"]
                correct = stats["correct"]
                result[model_name][sport] = {
                    "total": total,
                    "correct": correct,
                    "incorrect": total - correct,
                    "accuracy": round((correct / total) * 100, 2) if total > 0 else 0.0,
                }

        return result

    def get_model_performance_by_bet_type(
        self, model: str = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get model performance broken down by bet type"""
        predictions = self._get_verified_predictions()

        # Filter by model if specified
        if model:
            predictions = [p for p in predictions if p.get("model") == model]

        by_model_type = defaultdict(
            lambda: defaultdict(lambda: {"total": 0, "correct": 0})
        )

        for pred in predictions:
            model_name = pred.get("model", "unknown")
            bet_type = pred.get("bet_type", "unknown")

            by_model_type[model_name][bet_type]["total"] += 1
            if pred.get("prediction_correct", False):
                by_model_type[model_name][bet_type]["correct"] += 1

        result = {}
        for model_name, bet_types in by_model_type.items():
            result[model_name] = {}
            for bet_type, stats in bet_types.items():
                total = stats["total"]
                correct = stats["correct"]
                result[model_name][bet_type] = {
                    "total": total,
                    "correct": correct,
                    "incorrect": total - correct,
                    "accuracy": round((correct / total) * 100, 2) if total > 0 else 0.0,
                }

        return result

    def get_model_performance_over_time(
        self, model: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get daily performance for a specific model"""
        predictions = self._get_verified_predictions()
        predictions = [p for p in predictions if p.get("model") == model]

        by_date = defaultdict(lambda: {"total": 0, "correct": 0})

        for pred in predictions:
            verified_at = pred.get("outcome_verified_at")
            if verified_at:
                date = verified_at.split("T")[0]
                by_date[date]["total"] += 1
                if pred.get("prediction_correct", False):
                    by_date[date]["correct"] += 1

        result = []
        for date, stats in sorted(by_date.items()):
            total = stats["total"]
            correct = stats["correct"]
            result.append(
                {
                    "date": date,
                    "total": total,
                    "correct": correct,
                    "accuracy": round((correct / total) * 100, 2) if total > 0 else 0.0,
                }
            )

        return result[-days:]

    def get_model_comparison(self) -> List[Dict[str, Any]]:
        """Compare all models side by side"""
        summary = self.get_model_performance_summary()

        # Convert to list and sort by accuracy
        models = []
        for model_name, stats in summary.items():
            models.append(
                {
                    "model": model_name,
                    "accuracy": stats["accuracy"],
                    "total_predictions": stats["total_predictions"],
                    "correct": stats["correct_predictions"],
                    "incorrect": stats["incorrect_predictions"],
                    "sports": stats["sports_covered"],
                }
            )

        models.sort(key=lambda x: x["accuracy"], reverse=True)
        return models

    def get_model_confidence_analysis(self, model: str) -> Dict[str, Any]:
        """Analyze prediction accuracy by confidence level"""
        predictions = self._get_verified_predictions()
        predictions = [p for p in predictions if p.get("model") == model]

        # Group by confidence ranges
        confidence_ranges = {
            "high": {"min": 0.7, "max": 1.0, "total": 0, "correct": 0},
            "medium": {"min": 0.5, "max": 0.7, "total": 0, "correct": 0},
            "low": {"min": 0.0, "max": 0.5, "total": 0, "correct": 0},
        }

        for pred in predictions:
            confidence = float(pred.get("confidence", 0))

            for range_name, range_data in confidence_ranges.items():
                if range_data["min"] <= confidence < range_data["max"]:
                    range_data["total"] += 1
                    if pred.get("prediction_correct", False):
                        range_data["correct"] += 1
                    break

        result = {}
        for range_name, stats in confidence_ranges.items():
            total = stats["total"]
            correct = stats["correct"]
            result[range_name] = {
                "confidence_range": f"{int(stats['min']*100)}-{int(stats['max']*100)}%",
                "total": total,
                "correct": correct,
                "accuracy": round((correct / total) * 100, 2) if total > 0 else 0.0,
            }

        return result

    def _get_verified_predictions(self) -> List[Dict[str, Any]]:
        """Get all predictions with verified outcomes"""
        response = self.table.scan(
            FilterExpression="begins_with(pk, :pk) AND attribute_exists(outcome_verified_at)",
            ExpressionAttributeValues={":pk": "PREDICTION#"},
        )

        return response.get("Items", [])


def lambda_handler(event, context):
    """Lambda handler for model analytics"""
    table_name = os.getenv("DYNAMODB_TABLE")

    if not table_name:
        return {"statusCode": 500, "body": {"error": "Missing DYNAMODB_TABLE"}}

    try:
        analytics = ModelAnalytics(table_name)

        # Get query parameters
        query_params = event.get("queryStringParameters") or {}
        metric_type = query_params.get("type", "summary")
        model = query_params.get("model")

        # Route to appropriate metric
        if metric_type == "summary":
            data = analytics.get_model_performance_summary()
        elif metric_type == "by_sport":
            data = analytics.get_model_performance_by_sport(model)
        elif metric_type == "by_bet_type":
            data = analytics.get_model_performance_by_bet_type(model)
        elif metric_type == "over_time":
            if not model:
                return {
                    "statusCode": 400,
                    "body": {"error": "model parameter required for over_time"},
                }
            days = int(query_params.get("days", 30))
            data = analytics.get_model_performance_over_time(model, days)
        elif metric_type == "comparison":
            data = analytics.get_model_comparison()
        elif metric_type == "confidence":
            if not model:
                return {
                    "statusCode": 400,
                    "body": {"error": "model parameter required for confidence"},
                }
            data = analytics.get_model_confidence_analysis(model)
        else:
            return {
                "statusCode": 400,
                "body": {"error": f"Unknown metric type: {metric_type}"},
            }

        return {"statusCode": 200, "body": data}

    except Exception as e:
        print(f"Error in model analytics: {str(e)}")
        return {"statusCode": 500, "body": {"error": str(e)}}
