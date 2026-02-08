import os
from collections import defaultdict
from typing import Any, Dict, List

import boto3


class ModelAnalytics:
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.table = self.dynamodb.Table(table_name)

    def get_model_performance_summary(
        self, models: List[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get performance summary for each model"""
        analyses = self._get_verified_analyses(models)

        by_model = defaultdict(lambda: {"total": 0, "correct": 0, "sports": set()})

        for analysis in analyses:
            model = analysis.get("model", "unknown")
            by_model[model]["total"] += 1
            by_model[model]["sports"].add(analysis.get("sport", "unknown"))

            if analysis.get("analysis_correct", False):
                by_model[model]["correct"] += 1

        result = {}
        for model, stats in by_model.items():
            total = stats["total"]
            correct = stats["correct"]
            result[model] = {
                "model_name": model,
                "total_analyses": total,
                "correct_analyses": correct,
                "incorrect_analyses": total - correct,
                "accuracy": round((correct / total) * 100, 2) if total > 0 else 0.0,
                "sports_covered": list(stats["sports"]),
            }

        return result

    def get_model_performance_by_sport(
        self, model: str = None, models: List[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get model performance broken down by sport"""
        analyses = self._get_verified_analyses(models or ([model] if model else None))

        # Filter by model if specified
        if model:
            analyses = [a for a in analyses if a.get("model") == model]

        by_model_sport = defaultdict(
            lambda: defaultdict(lambda: {"total": 0, "correct": 0})
        )

        for analysis in analyses:
            model_name = analysis.get("model", "unknown")
            sport = analysis.get("sport", "unknown")

            by_model_sport[model_name][sport]["total"] += 1
            if analysis.get("analysis_correct", False):
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
        self, model: str = None, models: List[str] = None
    ) -> Dict[str, Dict[str, Any]]:
        """Get model performance broken down by bet type"""
        analyses = self._get_verified_analyses(models or ([model] if model else None))

        # Filter by model if specified
        if model:
            analyses = [a for a in analyses if a.get("model") == model]

        by_model_type = defaultdict(
            lambda: defaultdict(lambda: {"total": 0, "correct": 0})
        )

        for analysis in analyses:
            model_name = analysis.get("model", "unknown")
            bet_type = analysis.get("bet_type", "unknown")

            by_model_type[model_name][bet_type]["total"] += 1
            if analysis.get("analysis_correct", False):
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
        analyses = self._get_verified_analyses([model])
        analyses = [a for a in analyses if a.get("model") == model]

        by_date = defaultdict(lambda: {"total": 0, "correct": 0})

        for analysis in analyses:
            verified_at = analysis.get("outcome_verified_at")
            if verified_at:
                date = verified_at.split("T")[0]
                by_date[date]["total"] += 1
                if analysis.get("analysis_correct", False):
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
                    "total_analyses": stats["total_analyses"],
                    "correct": stats["correct_analyses"],
                    "incorrect": stats["incorrect_analyses"],
                    "sports": stats["sports_covered"],
                }
            )

        models.sort(key=lambda x: x["accuracy"], reverse=True)
        return models

    def get_model_confidence_analysis(self, model: str) -> Dict[str, Any]:
        """Analyze analysis accuracy by confidence level"""
        analyses = self._get_verified_analyses([model])
        analyses = [a for a in analyses if a.get("model") == model]

        # Group by confidence ranges
        confidence_ranges = {
            "high": {"min": 0.7, "max": 1.0, "total": 0, "correct": 0},
            "medium": {"min": 0.5, "max": 0.7, "total": 0, "correct": 0},
            "low": {"min": 0.0, "max": 0.5, "total": 0, "correct": 0},
        }

        for analysis in analyses:
            confidence = float(analysis.get("confidence", 0))

            for range_name, range_data in confidence_ranges.items():
                if range_data["min"] <= confidence < range_data["max"]:
                    range_data["total"] += 1
                    if analysis.get("analysis_correct", False):
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

    def get_recent_predictions(
        self, model: str, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get recent verified predictions for a model"""
        predictions = []
        sports = [
            "basketball_nba",
            "americanfootball_nfl",
            "baseball_mlb",
            "icehockey_nhl",
            "soccer_epl",
        ]
        bet_types = ["game", "prop"]

        for sport in sports:
            for bet_type in bet_types:
                pk = f"VERIFIED#{model}#{sport}#{bet_type}"

                response = self.table.query(
                    IndexName="VerifiedAnalysisGSI",
                    KeyConditionExpression="verified_analysis_pk = :pk",
                    ExpressionAttributeValues={":pk": pk},
                    ScanIndexForward=False,
                    Limit=limit,
                )

                for item in response.get("Items", []):
                    predictions.append(
                        {
                            "sport": item.get("sport"),
                            "bet_type": item.get("analysis_type"),
                            "game": f"{item.get('away_team', '')} @ {item.get('home_team', '')}".strip()
                            if item.get("home_team")
                            else item.get("player_name", "Unknown"),
                            "prediction": item.get("prediction"),
                            "player_name": item.get("player_name"),
                            "market_key": item.get("market_key"),
                            "correct": item.get("analysis_correct"),
                            "confidence": float(item.get("confidence", 0))
                            if item.get("confidence")
                            else 0,
                            "verified_at": item.get("outcome_verified_at"),
                        }
                    )

        # Sort by verified_at and return most recent
        predictions.sort(key=lambda x: x.get("verified_at", ""), reverse=True)
        return predictions[:limit]

    def get_confidence_distribution(self, model: str) -> Dict[str, Any]:
        """Get confidence distribution for a model's predictions"""
        analyses = self._get_verified_analyses([model])
        analyses = [a for a in analyses if a.get("model") == model]

        buckets = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}
        correct_by_bucket = {"0-20": 0, "20-40": 0, "40-60": 0, "60-80": 0, "80-100": 0}

        for analysis in analyses:
            confidence = float(analysis.get("confidence", 0)) * 100
            correct = analysis.get("analysis_correct", False)

            if confidence < 20:
                bucket = "0-20"
            elif confidence < 40:
                bucket = "20-40"
            elif confidence < 60:
                bucket = "40-60"
            elif confidence < 80:
                bucket = "60-80"
            else:
                bucket = "80-100"

            buckets[bucket] += 1
            if correct:
                correct_by_bucket[bucket] += 1

        result = {}
        for bucket, total in buckets.items():
            correct = correct_by_bucket[bucket]
            result[bucket] = {
                "total": total,
                "correct": correct,
                "accuracy": round((correct / total) * 100, 2) if total > 0 else 0.0,
            }

        return result

    def get_performance_over_time(
        self, model: str, days: int = 30
    ) -> List[Dict[str, Any]]:
        """Get model performance over time"""
        from collections import defaultdict

        analyses = self._get_verified_analyses([model])
        analyses = [a for a in analyses if a.get("model") == model]

        # Group by date
        by_date = defaultdict(lambda: {"total": 0, "correct": 0})

        for analysis in analyses:
            verified_at = analysis.get("outcome_verified_at", "")
            if not verified_at:
                continue

            date = verified_at.split("T")[0]  # Extract date part
            by_date[date]["total"] += 1
            if analysis.get("analysis_correct", False):
                by_date[date]["correct"] += 1

        # Convert to list and sort
        result = []
        for date, stats in sorted(by_date.items(), reverse=True)[:days]:
            result.append(
                {
                    "date": date,
                    "total": stats["total"],
                    "correct": stats["correct"],
                    "accuracy": round((stats["correct"] / stats["total"]) * 100, 2)
                    if stats["total"] > 0
                    else 0.0,
                }
            )

        return sorted(result, key=lambda x: x["date"])

    def _get_verified_analyses(self, models: List[str] = None) -> List[Dict[str, Any]]:
        """Get all analyses with verified outcomes using GSI"""
        items = []
        if models is None:
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
        sports = [
            "basketball_nba",
            "americanfootball_nfl",
            "baseball_mlb",
            "icehockey_nhl",
            "soccer_epl",
        ]
        bet_types = ["game", "prop"]

        for model in models:
            for sport in sports:
                for bet_type in bet_types:
                    pk = f"VERIFIED#{model}#{sport}#{bet_type}"

                    response = self.table.query(
                        IndexName="VerifiedAnalysisGSI",
                        KeyConditionExpression="verified_analysis_pk = :pk",
                        ExpressionAttributeValues={":pk": pk},
                    )

                    count = len(response.get("Items", []))
                    if count > 0:
                        print(f"Found {count} verified analyses for {pk}")

                    for item in response.get("Items", []):
                        items.append(
                            {
                                "model": item.get("model", "unknown"),
                                "sport": item.get("sport", "unknown"),
                                "bet_type": item.get("analysis_type", "unknown"),
                                "confidence": item.get("confidence", 0),
                                "analysis_correct": item.get("analysis_correct", False),
                                "outcome_verified_at": item.get("outcome_verified_at"),
                            }
                        )

        return items

    def get_cached_analytics(self, metric_key: str):
        """Get cached analytics from DynamoDB"""
        response = self.table.query(
            KeyConditionExpression="pk = :pk",
            ExpressionAttributeValues={":pk": f"ANALYTICS#{metric_key}"},
            ScanIndexForward=False,
            Limit=1,
        )

        items = response.get("Items", [])
        if items:
            return items[0].get("data", {})

        # Fallback to computing if cache miss
        print(f"Cache miss for {metric_key}, computing on-demand")
        if metric_key == "summary":
            return self.get_model_performance_summary()
        elif metric_key == "comparison":
            return self.get_model_comparison()
        return {}

    def compute_and_store_all_analytics(self):
        """Compute and store all analytics metrics"""
        import json
        from datetime import datetime
        from decimal import Decimal

        def convert_to_decimal(obj):
            """Convert floats to Decimal for DynamoDB"""
            return json.loads(json.dumps(obj), parse_float=Decimal)

        timestamp = datetime.now().isoformat()

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
        ]

        # Store summary
        summary = self.get_model_performance_summary()
        self.table.put_item(
            Item={
                "pk": "ANALYTICS#summary",
                "sk": timestamp,
                "data": convert_to_decimal(summary),
                "computed_at": timestamp,
            }
        )

        # Store by_sport for each model
        by_sport_all = self.get_model_performance_by_sport()
        for model in models:
            if model in by_sport_all:
                self.table.put_item(
                    Item={
                        "pk": "ANALYTICS#by_sport",
                        "sk": f"{model}#{timestamp}",
                        "data": convert_to_decimal(by_sport_all[model]),
                        "computed_at": timestamp,
                    }
                )

        # Store by_bet_type for each model
        by_bet_type_all = self.get_model_performance_by_bet_type()
        for model in models:
            if model in by_bet_type_all:
                self.table.put_item(
                    Item={
                        "pk": "ANALYTICS#by_bet_type",
                        "sk": f"{model}#{timestamp}",
                        "data": convert_to_decimal(by_bet_type_all[model]),
                        "computed_at": timestamp,
                    }
                )

        # Store confidence, over_time, and recent_predictions for each model
        for model in models:
            confidence = self.get_confidence_distribution(model)
            self.table.put_item(
                Item={
                    "pk": "ANALYTICS#confidence",
                    "sk": f"{model}#{timestamp}",
                    "data": convert_to_decimal(confidence),
                    "computed_at": timestamp,
                }
            )

            over_time = self.get_performance_over_time(model, 30)
            self.table.put_item(
                Item={
                    "pk": "ANALYTICS#over_time",
                    "sk": f"{model}#30#{timestamp}",
                    "data": convert_to_decimal(over_time),
                    "computed_at": timestamp,
                }
            )

            recent = self.get_recent_predictions(model, 20)
            self.table.put_item(
                Item={
                    "pk": "ANALYTICS#recent_predictions",
                    "sk": f"{model}#20#{timestamp}",
                    "data": convert_to_decimal(recent),
                    "computed_at": timestamp,
                }
            )

        print(f"Stored all analytics for {len(models)} models")
        return {"models": len(models)}


def lambda_handler(event, context):
    """Lambda handler for model analytics"""
    table_name = os.getenv("DYNAMODB_TABLE")

    if not table_name:
        return {"statusCode": 500, "body": {"error": "Missing DYNAMODB_TABLE"}}

    try:
        analytics = ModelAnalytics(table_name)

        # Get query parameters
        query_params = event.get("queryStringParameters") or {}

        # If no query params, this is a scheduled run - compute and store all analytics
        if not query_params:
            analytics.compute_and_store_all_analytics()
            return {
                "statusCode": 200,
                "body": {"message": "Analytics computed and stored"},
            }

        # Otherwise, read from cached analytics or compute on-demand
        metric_type = query_params.get("type", "summary")
        model = query_params.get("model")
        models_param = query_params.get("models")
        models = models_param.split(",") if models_param else None

        # Route to appropriate metric
        if metric_type == "summary":
            if models:
                # Compute on-demand for specific models
                data = analytics.get_model_performance_summary(models)
            else:
                data = analytics.get_cached_analytics("summary")
        elif metric_type == "by_sport":
            data = analytics.get_cached_analytics(
                f"by_sport#{model}" if model else "by_sport"
            )
        elif metric_type == "by_bet_type":
            data = analytics.get_cached_analytics(
                f"by_bet_type#{model}" if model else "by_bet_type"
            )
        elif metric_type == "over_time":
            if not model:
                return {
                    "statusCode": 400,
                    "body": {"error": "model parameter required for over_time"},
                }
            days = int(query_params.get("days", 30))
            data = analytics.get_cached_analytics(f"over_time#{model}#{days}")
        elif metric_type == "comparison":
            data = analytics.get_cached_analytics("comparison")
        elif metric_type == "confidence":
            if not model:
                return {
                    "statusCode": 400,
                    "body": {"error": "model parameter required for confidence"},
                }
            data = analytics.get_cached_analytics(f"confidence#{model}")
        elif metric_type == "recent_predictions":
            if not model:
                return {
                    "statusCode": 400,
                    "body": {
                        "error": "model parameter required for recent_predictions"
                    },
                }
            limit = int(query_params.get("limit", 20))
            data = analytics.get_recent_predictions(model, limit)
        else:
            return {
                "statusCode": 400,
                "body": {"error": f"Unknown metric type: {metric_type}"},
            }

        return {"statusCode": 200, "body": data}

    except Exception as e:
        print(f"Error in model analytics: {str(e)}")
        return {"statusCode": 500, "body": {"error": str(e)}}
