import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict

import boto3

from api.utils import create_response, decimal_to_float
from api.user import (
    handle_get_profile,
    handle_get_subscription,
    handle_update_profile,
    handle_upgrade_subscription,
)
from constants import SYSTEM_MODELS
from user_models import ModelPrediction, UserModel

# DynamoDB setup
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table_name = os.getenv("DYNAMODB_TABLE")
table = dynamodb.Table(table_name)


def calculate_roi(odds: int, confidence: float) -> dict:
    """Calculate ROI and risk level from odds and confidence"""
    if not odds:
        return {"roi": None, "risk_level": "unknown"}

    # Calculate implied probability from odds
    if odds < 0:
        implied_prob = abs(odds) / (abs(odds) + 100)
        roi_multiplier = 100 / abs(odds)
    else:
        implied_prob = 100 / (odds + 100)
        roi_multiplier = odds / 100

    # Calculate expected ROI: (confidence * roi_multiplier) - (1 - confidence)
    expected_roi = (confidence * roi_multiplier) - (1 - confidence)

    # Determine risk level
    if confidence >= 0.65:
        risk_level = "conservative"
    elif confidence >= 0.55:
        risk_level = "moderate"
    else:
        risk_level = "aggressive"

    return {
        "roi": round(expected_roi * 100, 1),  # As percentage
        "risk_level": risk_level,
        "implied_probability": round(implied_prob * 100, 1),
    }


def lambda_handler(event, context):
    """
    Main Lambda handler for API requests
    
    NOTE: The following endpoints have been migrated to separate Lambda functions:
    - /health, /benny/dashboard, /compliance/log -> api.misc.lambda_handler
    - /games, /sports, /bookmakers, /player-props -> api.games.lambda_handler
    - /analyses, /top-analysis -> api.analyses.lambda_handler
    """
    try:
        print(f"Lambda handler called with event: {event}")

        http_method = event.get("httpMethod", "")
        path = event.get("path", "")
        query_params = event.get("queryStringParameters") or {}

        print(f"Processing request: {http_method} {path}")

        # Handle CORS preflight
        if http_method == "OPTIONS":
            return create_response(200, {"message": "CORS preflight"})

        # Route requests (remaining endpoints only)
        if path == "/profile" and http_method == "GET":
            return handle_get_profile(query_params)
        elif path == "/profile" and http_method == "PUT":
            body = json.loads(event.get("body", "{}"))
            return handle_update_profile(body)
        elif path == "/subscription":
            return handle_get_subscription(query_params)
        elif path == "/subscription/upgrade" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))
            return handle_upgrade_subscription(body)
        elif path == "/analytics":
            return handle_get_analytics(query_params)
        elif path == "/model-performance":
            return handle_get_model_performance(query_params)
        elif path == "/model-comparison":
            return handle_get_model_comparison(query_params)
        elif path == "/model-rankings":
            return handle_get_model_rankings(query_params)
        elif path == "/custom-data" and http_method == "GET":
            return handle_list_custom_data(query_params)
        elif path == "/custom-data/upload" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))
            return handle_upload_custom_data(body)
        elif path.startswith("/custom-data/") and http_method == "DELETE":
            dataset_id = path.split("/")[-1]
            return handle_delete_custom_data(dataset_id, query_params)
        elif path == "/user-models" and http_method == "GET":
            return handle_list_user_models(query_params)
        elif path == "/user-models/predictions" and http_method == "GET":
            return handle_get_user_model_predictions(query_params)
        elif path == "/user-models" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))
            return handle_create_user_model(body)
        elif (
            path.startswith("/user-models/")
            and "/backtests" in path
            and http_method == "GET"
        ):
            model_id = path.split("/")[2]
            return handle_list_backtests(model_id, query_params)
        elif (
            path.startswith("/user-models/")
            and "/backtests" in path
            and http_method == "POST"
        ):
            model_id = path.split("/")[2]
            body = json.loads(event.get("body", "{}"))
            return handle_create_backtest(model_id, body)
        elif path.startswith("/backtests/") and http_method == "GET":
            backtest_id = path.split("/")[-1]
            return handle_get_backtest(backtest_id, query_params)
        elif path.startswith("/user-models/") and http_method == "GET":
            model_id = path.split("/")[-1]
            return handle_get_user_model(model_id, query_params)
        elif path.startswith("/user-models/") and http_method == "PUT":
            model_id = path.split("/")[-1]
            body = json.loads(event.get("body", "{}"))
            return handle_update_user_model(model_id, body)
        elif path.startswith("/user-models/") and http_method == "DELETE":
            model_id = path.split("/")[-1]
            return handle_delete_user_model(model_id, query_params)
        elif path.startswith("/user-models/") and "/performance" in path:
            model_id = path.split("/")[2]
            return handle_get_user_model_performance(model_id)
        else:
            return create_response(404, {"error": "Endpoint not found"})

    except Exception as e:
        return create_response(500, {"error": f"Internal server error: {str(e)}"})


# ============================================================================
# MIGRATED ENDPOINTS - Functions below have been moved to modular handlers
# ============================================================================
# - handle_health() -> api/misc.py
# - handle_get_games() -> api/games.py
# - handle_get_sports() -> api/games.py
# - handle_get_bookmakers() -> api/games.py
# - handle_get_benny_dashboard() -> api/misc.py
# - handle_get_player_props() -> api/games.py
# - handle_compliance_log() -> api/misc.py
# - handle_get_analyses() -> api/analyses.py
# - handle_get_top_analysis() -> api/analyses.py
# ============================================================================


    """Get model analytics data from DynamoDB cache"""
    try:
        print(f"Analytics request - query_params: {query_params}")
        metric_type = query_params.get("type", "summary")
        days = int(query_params.get("days", 90))  # Default to 90 days
        print(f"Metric type: {metric_type}, days: {days}")

        # Handle weights separately (not cached)
        if metric_type == "weights":
            from ml.dynamic_weighting import DynamicModelWeighting

            weighting = DynamicModelWeighting()
            sport = query_params.get("sport", "basketball_nba")
            bet_type = query_params.get("bet_type", "game")

            all_models = [
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
            weights = weighting.get_model_weights(sport, bet_type, models=all_models)
            model_metrics = {}
            for model_name in all_models:
                accuracy = weighting.get_recent_accuracy(model_name, sport, bet_type)
                brier = weighting.get_recent_brier_score(model_name, sport, bet_type)
                model_metrics[model_name] = {
                    "weight": weights[model_name],
                    "recent_accuracy": accuracy,
                    "recent_brier_score": brier,
                }

            data = {
                "sport": sport,
                "bet_type": bet_type,
                "lookback_days": weighting.lookback_days,
                "model_weights": model_metrics,
            }
            return create_response(200, decimal_to_float(data))

        # Read cached analytics from DynamoDB
        model = query_params.get("model")

        # Build partition key for query
        if metric_type == "summary":
            pk = "ANALYTICS#summary"
        elif metric_type in [
            "by_sport",
            "by_bet_type",
            "confidence",
            "over_time",
            "recent_predictions",
        ]:
            if not model:
                return create_response(
                    400, {"error": f"model parameter required for {metric_type}"}
                )
            # Special case: model=all for by_bet_type returns all models
            if model == "all" and metric_type == "by_bet_type":
                from model_analytics import ModelAnalytics

                analytics = ModelAnalytics(table_name)
                data = analytics.get_model_performance_by_bet_type(days=days)
                return create_response(200, decimal_to_float(data))
            pk = f"ANALYTICS#{metric_type}"
        else:
            return create_response(
                400, {"error": f"Unknown metric type: {metric_type}"}
            )

        print(f"Querying DynamoDB - pk: {pk}, model: {model}")

        # Query DynamoDB for cached analytics (get latest by timestamp)
        if model and metric_type != "summary":
            response = table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)",
                ExpressionAttributeValues={":pk": pk, ":sk": model},
                ScanIndexForward=False,
                Limit=1,
            )
        else:
            response = table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                ScanIndexForward=False,
                Limit=1,
            )

        print(f"DynamoDB response - Count: {response.get('Count')}")

        if not response.get("Items"):
            # Cache miss - compute on-demand with time filter
            from model_analytics import ModelAnalytics

            analytics = ModelAnalytics(table_name)

            if metric_type == "summary":
                data = analytics.get_model_performance_summary(days=days)
            elif metric_type == "by_sport":
                data = analytics.get_model_performance_by_sport(model=model, days=days)
            elif metric_type == "by_bet_type":
                data = analytics.get_model_performance_by_bet_type(
                    model=model, days=days
                )
            elif metric_type == "confidence":
                data = analytics.get_model_confidence_analysis(model=model, days=days)
            elif metric_type == "over_time":
                data = analytics.get_performance_over_time(model=model, days=days)
            elif metric_type == "recent_predictions":
                limit = int(query_params.get("limit", 20))
                data = analytics.get_recent_predictions(model=model, limit=limit)
            else:
                return create_response(
                    400, {"error": f"Unknown metric type: {metric_type}"}
                )

            return create_response(200, decimal_to_float(data))

        data = response["Items"][0].get("data", {})
        return create_response(200, decimal_to_float(data))

    except Exception as e:
        print(f"Error invoking model analytics: {str(e)}")
        return create_response(500, {"error": str(e)})


def handle_get_model_performance(query_params: Dict[str, str]):
    """Get model performance metrics"""
    try:
        from model_performance import ModelPerformanceTracker

        tracker = ModelPerformanceTracker(table_name)
        sport = query_params.get("sport", "basketball_nba")
        model = query_params.get("model")
        days = int(query_params.get("days", 30))

        if model:
            # Get performance for specific model
            performance = tracker.get_model_performance(model, sport, days)
            return create_response(
                200,
                {
                    "model": model,
                    "sport": sport,
                    "days": days,
                    "performance": decimal_to_float(performance),
                },
            )
        else:
            # Get performance for all models
            performance = tracker.get_all_models_performance(sport, days)
            return create_response(
                200,
                {
                    "sport": sport,
                    "days": days,
                    "models": decimal_to_float(performance),
                },
            )

    except Exception as e:
        return create_response(
            500, {"error": f"Error fetching model performance: {str(e)}"}
        )


def handle_get_model_comparison(query_params: Dict[str, str]):
    """Get model comparison with original vs inverse performance"""
    try:
        from api_middleware import check_feature_access

        sport = query_params.get("sport", "basketball_nba")
        days = int(query_params.get("days", 90))
        user_id = query_params.get("user_id")

        # Handle "all sports" request
        if sport == "all":
            all_sports = [
                "basketball_nba",
                "americanfootball_nfl",
                "baseball_mlb",
                "icehockey_nhl",
                "soccer_epl",
            ]
            all_models = []

            for s in all_sports:
                # Try cache first
                cache_key = f"MODEL_COMPARISON#{s}#{days}"
                try:
                    cache_response = table.get_item(
                        Key={"pk": "CACHE", "sk": cache_key}
                    )
                    if "Item" in cache_response:
                        cached_items = cache_response["Item"]["data"]
                        # Add sport field to cached items if missing
                        for item in cached_items:
                            if "sport" not in item:
                                item["sport"] = s
                        all_models.extend(cached_items)
                        continue
                except Exception:
                    pass

                # Compute if not cached
                cutoff_time = (
                    (datetime.utcnow() - timedelta(days=days)).isoformat()
                    if days < 9999
                    else "2000-01-01T00:00:00"
                )

                for model in SYSTEM_MODELS:
                    if model == "benny" and not user_id:
                        continue
                    model_data = _get_model_comparison_data(
                        model, s, cutoff_time, is_user_model=False
                    )
                    if model_data:
                        all_models.extend(model_data)

            # Filter Benny based on access
            if user_id:
                from feature_flags import get_user_limits

                limits = get_user_limits(user_id)
                if not limits.get("benny_ai", False):
                    all_models = [m for m in all_models if m.get("model") != "benny"]
            else:
                all_models = [m for m in all_models if m.get("model") != "benny"]

            # Sort by best accuracy
            all_models.sort(
                key=lambda x: max(x["original_accuracy"], x["inverse_accuracy"]),
                reverse=True,
            )

            return create_response(
                200,
                {
                    "sport": "all",
                    "days": days,
                    "models": all_models,
                    "cached": False,
                },
            )

        # Try to get from cache first
        cache_key = f"MODEL_COMPARISON#{sport}#{days}"
        try:
            cache_response = table.get_item(Key={"pk": "CACHE", "sk": cache_key})
            if "Item" in cache_response:
                cached_data = cache_response["Item"]["data"]
                print(f"Cache hit for {cache_key}")

                # Filter out Benny if user doesn't have access
                from feature_flags import get_user_limits

                if user_id:
                    limits = get_user_limits(user_id)
                    if not limits.get("benny_ai", False):
                        cached_data = [
                            m for m in cached_data if m.get("model") != "benny"
                        ]
                else:
                    # No user_id means no access to Benny
                    cached_data = [m for m in cached_data if m.get("model") != "benny"]

                # If user_id provided and feature enabled, add user models to cached data
                if user_id:
                    access_check = check_feature_access(user_id, "user_models")
                    if access_check["allowed"]:
                        from user_models import UserModel
                        from datetime import datetime, timedelta

                        if days >= 9999:
                            cutoff_time = "2000-01-01T00:00:00"
                        else:
                            cutoff_time = (
                                datetime.utcnow() - timedelta(days=days)
                            ).isoformat()

                        user_models = UserModel.list_by_user(user_id)
                        for user_model in user_models:
                            if (
                                user_model.sport == sport
                                and user_model.status == "active"
                            ):
                                model_data = _get_model_comparison_data(
                                    user_model.model_id,
                                    sport,
                                    cutoff_time,
                                    is_user_model=True,
                                    model_name=user_model.name,
                                )
                                if model_data:
                                    cached_data.extend(model_data)

                    # Re-sort with user models included
                    cached_data.sort(
                        key=lambda x: max(
                            x["original_accuracy"], x["inverse_accuracy"]
                        ),
                        reverse=True,
                    )

                return create_response(
                    200,
                    {
                        "sport": sport,
                        "days": days,
                        "models": cached_data,
                        "cached": True,
                        "computed_at": cache_response["Item"].get("computed_at"),
                    },
                )
        except Exception as cache_error:
            print(f"Cache miss or error: {cache_error}")

        # Fallback: compute on-demand if cache miss
        print(f"Computing model comparison on-demand for {sport}, {days} days")
        from datetime import datetime, timedelta

        # Handle "all time" query (days >= 9999 means no time filter)
        if days >= 9999:
            cutoff_time = "2000-01-01T00:00:00"  # Far past date = all time
        else:
            cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()

        comparison = []

        # Filter system models based on user access
        from feature_flags import get_user_limits

        allowed_models = list(SYSTEM_MODELS)
        if user_id:
            limits = get_user_limits(user_id)
            if not limits.get("benny_ai", False):
                allowed_models = [m for m in allowed_models if m != "benny"]
        else:
            # No user_id means no access to Benny
            allowed_models = [m for m in allowed_models if m != "benny"]

        # Add system models
        for model in allowed_models:
            model_data = _get_model_comparison_data(
                model, sport, cutoff_time, is_user_model=False
            )
            if model_data:
                comparison.extend(
                    model_data
                )  # extend instead of append (returns list now)

        # Add user models if user_id provided
        if user_id:
            from user_models import UserModel

            user_models = UserModel.list_by_user(user_id)

            for user_model in user_models:
                if user_model.sport == sport and user_model.status == "active":
                    model_data = _get_model_comparison_data(
                        user_model.model_id,
                        sport,
                        cutoff_time,
                        is_user_model=True,
                        model_name=user_model.name,
                    )
                    if model_data:
                        comparison.extend(model_data)  # extend instead of append

        # Sort by best performing (either original or inverse)
        comparison.sort(
            key=lambda x: max(x["original_accuracy"], x["inverse_accuracy"]),
            reverse=True,
        )

        return create_response(
            200,
            {
                "sport": sport,
                "days": days,
                "models": comparison,
                "summary": {
                    "total_models": len(comparison),
                    "inverse_recommended": sum(
                        1 for m in comparison if m["recommendation"] == "INVERSE"
                    ),
                    "original_recommended": sum(
                        1 for m in comparison if m["recommendation"] == "ORIGINAL"
                    ),
                    "avoid": sum(
                        1 for m in comparison if m["recommendation"] == "AVOID"
                    ),
                },
            },
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return create_response(
            500, {"error": f"Error fetching model comparison: {str(e)}"}
        )


def handle_get_model_rankings(query_params: Dict[str, str]):
    """Get model rankings by ROI and profitability metrics"""
    try:
        sport = query_params.get("sport", "basketball_nba")
        days = int(query_params.get("days", 30))
        user_id = query_params.get("user_id")
        mode = query_params.get("mode", "both")  # original, inverse, or both

        from datetime import datetime, timedelta

        cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()

        rankings = []

        # Calculate ROI for system models
        for model in SYSTEM_MODELS:
            model_data = _calculate_model_roi(
                model, sport, cutoff_time, is_user_model=False, mode=mode
            )
            if model_data:
                rankings.extend(model_data)

        # Calculate ROI for user models
        if user_id:
            from user_models import UserModel

            user_models = UserModel.list_by_user(user_id)
            for user_model in user_models:
                if user_model.sport == sport and user_model.status == "active":
                    model_data = _calculate_model_roi(
                        user_model.model_id,
                        sport,
                        cutoff_time,
                        is_user_model=True,
                        model_name=user_model.name,
                        mode=mode,
                    )
                    if model_data:
                        rankings.extend(model_data)

        # Sort by ROI descending
        rankings.sort(key=lambda x: x["roi"], reverse=True)

        return create_response(
            200,
            {
                "sport": sport,
                "days": days,
                "mode": mode,
                "rankings": rankings,
                "summary": {
                    "total_models": len(rankings),
                    "profitable": sum(1 for r in rankings if r["roi"] > 0),
                    "unprofitable": sum(1 for r in rankings if r["roi"] < 0),
                    "avg_roi": (
                        round(sum(r["roi"] for r in rankings) / len(rankings), 3)
                        if rankings
                        else 0
                    ),
                },
            },
        )

    except Exception as e:
        import traceback

        traceback.print_exc()
        return create_response(500, {"error": f"Error fetching rankings: {str(e)}"})


def _calculate_model_roi(
    model_id: str,
    sport: str,
    cutoff_time: str,
    is_user_model: bool = False,
    model_name: str = None,
    mode: str = "both",
) -> list:
    """Calculate ROI metrics for a model (returns list for original/inverse)"""
    try:
        from boto3.dynamodb.conditions import Key

        results = []

        # Determine which modes to calculate
        modes_to_calc = []
        if mode in ["original", "both"]:
            modes_to_calc.append(("original", ""))
        if mode in ["inverse", "both"]:
            modes_to_calc.append(("inverse", "#inverse"))

        for mode_name, pk_suffix in modes_to_calc:
            # Query verified predictions
            if is_user_model:
                pk = f"VERIFIED#{model_id}#{sport}#game{pk_suffix}"
            else:
                pk = f"VERIFIED#{model_id}#{sport}#game{pk_suffix}"

            response = table.query(
                IndexName="VerifiedAnalysisGSI",
                KeyConditionExpression=Key("verified_analysis_pk").eq(pk)
                & Key("verified_analysis_sk").gte(cutoff_time),
                Limit=1000,
            )
            items = response.get("Items", [])

            if not items:
                continue

            # Calculate metrics
            total_bets = len(items)
            wins = sum(1 for item in items if item.get("analysis_correct"))
            losses = total_bets - wins
            win_rate = wins / total_bets if total_bets > 0 else 0

            # Calculate profit/loss assuming $100 bets with average odds
            total_profit = 0
            total_wagered = total_bets * 100
            odds_sum = 0
            odds_count = 0

            for item in items:
                # Extract odds from outcomes if available
                outcomes = item.get("outcomes", [])
                if outcomes and len(outcomes) > 0:
                    # Use first outcome's odds as proxy
                    odds = float(outcomes[0].get("price", 0))
                    odds_sum += odds
                    odds_count += 1

                    # Calculate profit for this bet
                    if item.get("analysis_correct"):
                        if odds > 0:
                            profit = (100 * odds) / 100
                        else:
                            profit = 100 / (abs(odds) / 100)
                        total_profit += profit
                    else:
                        total_profit -= 100

            avg_odds = odds_sum / odds_count if odds_count > 0 else 0
            roi = (total_profit / total_wagered) if total_wagered > 0 else 0

            # Calculate Sharpe ratio (simplified: returns / volatility)
            if total_bets > 1:
                avg_return = total_profit / total_bets
                variance = sum(
                    ((100 if item.get("analysis_correct") else -100) - avg_return) ** 2
                    for item in items
                ) / (total_bets - 1)
                std_dev = variance**0.5
                sharpe = avg_return / std_dev if std_dev > 0 else 0
            else:
                sharpe = 0

            results.append(
                {
                    "model": model_name or model_id,
                    "model_id": model_id,
                    "mode": mode_name,
                    "is_user_model": is_user_model,
                    "total_bets": total_bets,
                    "wins": wins,
                    "losses": losses,
                    "win_rate": round(win_rate, 3),
                    "avg_odds": round(avg_odds, 0),
                    "profit": round(total_profit, 2),
                    "roi": round(roi, 3),
                    "sharpe_ratio": round(sharpe, 3),
                }
            )

        return results

    except Exception as e:
        print(f"Error calculating ROI for {model_id}: {e}")
        return []


def _get_model_comparison_data(
    model_id: str,
    sport: str,
    cutoff_time: str,
    is_user_model: bool = False,
    model_name: str = None,
) -> list:
    """Get comparison data for a single model (returns list with separate game/prop entries)"""
    try:
        from boto3.dynamodb.conditions import Key

        results = []

        # Query games and props separately
        for bet_type in ["game", "prop"]:
            original_items = []
            inverse_items = []

            # Query original predictions
            if is_user_model:
                original_pk = f"VERIFIED#{model_id}#{sport}#{bet_type}"
            else:
                original_pk = f"VERIFIED#{model_id}#{sport}#{bet_type}"

            original_response = table.query(
                IndexName="VerifiedAnalysisGSI",
                KeyConditionExpression=Key("verified_analysis_pk").eq(original_pk)
                & Key("verified_analysis_sk").gte(cutoff_time),
                Limit=5000,
            )
            original_items = original_response.get("Items", [])

            # Query inverse predictions
            inverse_pk = f"{original_pk}#inverse"
            inverse_response = table.query(
                IndexName="VerifiedAnalysisGSI",
                KeyConditionExpression=Key("verified_analysis_pk").eq(inverse_pk)
                & Key("verified_analysis_sk").gte(cutoff_time),
                Limit=5000,
            )
            inverse_items = inverse_response.get("Items", [])

            if not original_items:
                continue  # Skip if no data for this bet type

            # Calculate original metrics
            original_total = len(original_items)
            original_correct = sum(
                1 for item in original_items if item.get("analysis_correct")
            )
            original_accuracy = (
                original_correct / original_total if original_total > 0 else 0
            )

            # Calculate inverse metrics
            inverse_total = len(inverse_items)
            inverse_correct = sum(
                1 for item in inverse_items if item.get("analysis_correct")
            )
            inverse_accuracy = (
                inverse_correct / inverse_total if inverse_total > 0 else 0
            )

            # Determine recommendation
            if inverse_accuracy > original_accuracy and inverse_accuracy > 0.5:
                recommendation = "INVERSE"
            elif original_accuracy > 0.5:
                recommendation = "ORIGINAL"
            else:
                recommendation = "AVOID"

            results.append(
                {
                    "model": model_name or model_id,
                    "model_id": model_id,
                    "sport": sport,
                    "bet_type": bet_type,
                    "is_user_model": is_user_model,
                    "sample_size": original_total,
                    "original_accuracy": round(original_accuracy, 3),
                    "original_correct": original_correct,
                    "original_total": original_total,
                    "inverse_accuracy": round(inverse_accuracy, 3),
                    "inverse_correct": inverse_correct,
                    "inverse_total": inverse_total,
                    "recommendation": recommendation,
                    "accuracy_diff": round(inverse_accuracy - original_accuracy, 3),
                }
            )

        return results

    except Exception as e:
        print(f"Error getting comparison data for {model_id}: {e}")
        return []


# User Models API Handlers
def handle_list_user_models(query_params: Dict[str, str]):
    """List all models for a user"""
    try:
        from user_models import UserModel
        from api_middleware import check_feature_access

        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id parameter required"})

        # Check feature access
        access_check = check_feature_access(user_id, "user_models")
        if not access_check["allowed"]:
            return create_response(403, {"error": access_check["error"]})

        models = UserModel.list_by_user(user_id)
        return create_response(
            200, {"models": [decimal_to_float(m.to_dynamodb()) for m in models]}
        )
    except Exception as e:
        return create_response(500, {"error": f"Error listing models: {str(e)}"})


def handle_create_user_model(body: Dict[str, Any]):
    """Create a new user model"""
    try:
        from user_models import UserModel, validate_model_config
        from api_middleware import check_feature_access, check_resource_limit

        user_id = body.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id is required"})

        # Check feature access
        access_check = check_feature_access(user_id, "user_models")
        if not access_check["allowed"]:
            return create_response(403, {"error": access_check["error"]})

        # Check model limit
        current_models = len(UserModel.list_by_user(user_id))
        limit_check = check_resource_limit(user_id, "user_model", current_models)
        if not limit_check["allowed"]:
            return create_response(403, {"error": limit_check["error"]})

        # Validate required fields
        required = ["name", "sport", "bet_types", "data_sources"]
        for field in required:
            if field not in body:
                return create_response(
                    400, {"error": f"Missing required field: {field}"}
                )

        # Validate model configuration
        is_valid, error = validate_model_config(body)
        if not is_valid:
            return create_response(400, {"error": error})

        # Create model
        model = UserModel(
            user_id=user_id,
            name=body["name"],
            description=body.get("description", ""),
            sport=body["sport"],
            bet_types=body["bet_types"],
            data_sources=body["data_sources"],
            min_confidence=body.get("min_confidence", 0.6),
            status=body.get("status", "active"),
            auto_adjust_weights=body.get("auto_adjust_weights", False),
        )
        model.save()

        return create_response(
            201,
            {
                "message": "Model created successfully",
                "model": decimal_to_float(model.to_dynamodb()),
            },
        )
    except Exception as e:
        return create_response(500, {"error": f"Error creating model: {str(e)}"})


def handle_get_user_model(model_id: str, query_params: Dict[str, str]):
    """Get a specific user model"""
    try:
        from user_models import UserModel

        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id parameter required"})

        model = UserModel.get(user_id, model_id)
        if not model:
            return create_response(404, {"error": "Model not found"})

        return create_response(200, {"model": decimal_to_float(model.to_dynamodb())})
    except Exception as e:
        return create_response(500, {"error": f"Error fetching model: {str(e)}"})


def handle_update_user_model(model_id: str, body: Dict[str, Any]):
    """Update an existing user model"""
    try:
        from user_models import UserModel, validate_model_config

        user_id = body.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id required in body"})

        # Get existing model
        model = UserModel.get(user_id, model_id)
        if not model:
            return create_response(404, {"error": "Model not found"})

        # Update fields
        if "name" in body:
            model.name = body["name"]
        if "description" in body:
            model.description = body["description"]
        if "data_sources" in body:
            # Validate new configuration
            test_config = {
                "user_id": user_id,
                "name": model.name,
                "sport": model.sport,
                "bet_types": model.bet_types,
                "data_sources": body["data_sources"],
            }
            is_valid, error = validate_model_config(test_config)
            if not is_valid:
                return create_response(400, {"error": error})
            model.data_sources = body["data_sources"]
        if "min_confidence" in body:
            model.min_confidence = body["min_confidence"]
        if "status" in body:
            model.status = body["status"]
        if "auto_adjust_weights" in body:
            model.auto_adjust_weights = body["auto_adjust_weights"]

        model.save()

        return create_response(
            200,
            {
                "message": "Model updated successfully",
                "model": decimal_to_float(model.to_dynamodb()),
            },
        )
    except Exception as e:
        return create_response(500, {"error": f"Error updating model: {str(e)}"})


def handle_delete_user_model(model_id: str, query_params: Dict[str, str]):
    """Delete a user model"""
    try:
        from user_models import UserModel

        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id parameter required"})

        # Get model to verify it exists
        model = UserModel.get(user_id, model_id)
        if not model:
            return create_response(404, {"error": "Model not found"})

        model.delete()
        return create_response(200, {"message": "Model deleted successfully"})
    except Exception as e:
        return create_response(500, {"error": f"Error deleting model: {str(e)}"})


def handle_create_backtest(model_id: str, body: Dict[str, Any]):
    """Create a backtest for a user model"""
    try:
        from backtest_engine import BacktestEngine
        from user_models import UserModel

        user_id = body.get("user_id")
        start_date = body.get("start_date")
        end_date = body.get("end_date")

        if not all([user_id, start_date, end_date]):
            return create_response(
                400, {"error": "user_id, start_date, and end_date required"}
            )

        # Get model config
        model = UserModel.get(user_id, model_id)
        if not model:
            return create_response(404, {"error": "Model not found"})

        # Run backtest
        engine = BacktestEngine()
        result = engine.run_backtest(
            user_id, model_id, model.to_dynamodb(), start_date, end_date
        )

        return create_response(200, decimal_to_float(result))
    except Exception as e:
        return create_response(500, {"error": f"Error creating backtest: {str(e)}"})


def handle_list_backtests(model_id: str, query_params: Dict[str, str]):
    """List backtests for a model"""
    try:
        from backtest_engine import BacktestEngine

        backtests = BacktestEngine.list_backtests(model_id)
        return create_response(200, {"backtests": decimal_to_float(backtests)})
    except Exception as e:
        return create_response(500, {"error": f"Error listing backtests: {str(e)}"})


def handle_get_backtest(backtest_id: str, query_params: Dict[str, str]):
    """Get a specific backtest"""
    try:
        from backtest_engine import BacktestEngine

        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id parameter required"})

        backtest = BacktestEngine.get_backtest(user_id, backtest_id)
        if not backtest:
            return create_response(404, {"error": "Backtest not found"})

        return create_response(200, decimal_to_float(backtest))
    except Exception as e:
        return create_response(500, {"error": f"Error getting backtest: {str(e)}"})


def handle_get_user_model_performance(model_id: str):
    """Get performance metrics for a user model"""
    try:
        from user_models import ModelPrediction

        performance = ModelPrediction.get_performance(model_id)

        return create_response(
            200, {"model_id": model_id, "performance": decimal_to_float(performance)}
        )
    except Exception as e:
        return create_response(
            500, {"error": f"Error fetching model performance: {str(e)}"}
        )


def handle_get_user_model_predictions(query_params: Dict[str, str]):
    """Get predictions for user's models"""
    try:
        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id is required"})

        # Get all user's models
        models = UserModel.list_by_user(user_id)

        # Get predictions for each model
        all_predictions = []
        for model in models:
            predictions = ModelPrediction.list_by_model(model.model_id, limit=50)
            for pred in predictions:
                all_predictions.append(
                    {
                        "model_id": pred.model_id,
                        "model_name": model.name,
                        "game_id": pred.game_id,
                        "sport": pred.sport,
                        "prediction": pred.prediction,
                        "confidence": pred.confidence,
                        "reasoning": pred.reasoning,
                        "bet_type": pred.bet_type,
                        "home_team": pred.home_team,
                        "away_team": pred.away_team,
                        "commence_time": pred.commence_time,
                        "outcome": pred.outcome,
                        "created_at": pred.created_at,
                    }
                )

        return create_response(200, {"predictions": decimal_to_float(all_predictions)})
    except Exception as e:
        return create_response(500, {"error": f"Error fetching predictions: {str(e)}"})


def handle_list_custom_data(query_params: Dict[str, str]):
    """List user's custom datasets"""
    try:
        from custom_data import CustomDataset
        from api_middleware import check_feature_access

        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id is required"})

        # Check feature access
        access = check_feature_access(user_id, "custom_data")
        if not access["allowed"]:
            return create_response(403, {"error": access["error"]})

        datasets = CustomDataset.list_by_user(user_id)

        return create_response(
            200,
            {
                "datasets": [
                    {
                        "dataset_id": d.dataset_id,
                        "name": d.name,
                        "description": d.description,
                        "sport": d.sport,
                        "data_type": d.data_type,
                        "columns": d.columns,
                        "row_count": d.row_count,
                        "created_at": d.created_at,
                    }
                    for d in datasets
                ]
            },
        )
    except Exception as e:
        return create_response(500, {"error": f"Error listing datasets: {str(e)}"})


def handle_upload_custom_data(body: Dict[str, Any]):
    """Upload custom dataset"""
    try:
        import csv
        import io
        import uuid

        from custom_data import CustomDataset, validate_dataset
        from api_middleware import check_feature_access, check_resource_limit

        # Validate required fields
        required = ["user_id", "name", "sport", "data_type", "data"]
        for field in required:
            if field not in body:
                return create_response(
                    400, {"error": f"Missing required field: {field}"}
                )

        user_id = body["user_id"]

        # Check feature access
        access = check_feature_access(user_id, "custom_data")
        if not access["allowed"]:
            return create_response(403, {"error": access["error"]})

        # Check dataset limit
        current_datasets = CustomDataset.list_by_user(user_id)
        limit_check = check_resource_limit(user_id, "dataset", len(current_datasets))
        if not limit_check["allowed"]:
            return create_response(403, {"error": limit_check["error"]})
        name = body["name"]
        description = body.get("description", "")
        sport = body["sport"]
        data_type = body["data_type"]

        # Parse data (CSV or JSON)
        data_str = body["data"]
        file_format = body.get("format", "csv")

        if file_format == "csv":
            # Parse CSV
            csv_reader = csv.DictReader(io.StringIO(data_str))
            data = list(csv_reader)
        else:
            # Parse JSON
            data = json.loads(data_str)

        # Validate dataset
        is_valid, error = validate_dataset(data, data_type)
        if not is_valid:
            return create_response(400, {"error": error})

        # Create dataset
        dataset = CustomDataset(
            user_id=user_id,
            name=name,
            description=description,
            sport=sport,
            data_type=data_type,
            columns=list(data[0].keys()),
            s3_key=f"{user_id}/{uuid.uuid4().hex}.json",
            row_count=len(data),
        )

        # Upload to S3
        s3 = boto3.client("s3", region_name="us-east-1")
        bucket = os.environ.get("CUSTOM_DATA_BUCKET", "dev-custom-data-bucket")
        s3.put_object(
            Bucket=bucket, Key=dataset.s3_key, Body=json.dumps(data).encode("utf-8")
        )

        # Save metadata
        dataset.save()

        return create_response(
            201,
            {
                "message": "Dataset uploaded successfully",
                "dataset": {
                    "dataset_id": dataset.dataset_id,
                    "name": dataset.name,
                    "row_count": dataset.row_count,
                },
            },
        )
    except Exception as e:
        return create_response(500, {"error": f"Error uploading dataset: {str(e)}"})


def handle_delete_custom_data(dataset_id: str, query_params: Dict[str, str]):
    """Delete custom dataset"""
    try:
        from custom_data import CustomDataset
        from api_middleware import check_feature_access

        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id is required"})

        # Check feature access
        access = check_feature_access(user_id, "custom_data")
        if not access["allowed"]:
            return create_response(403, {"error": access["error"]})

        dataset = CustomDataset.get(user_id, dataset_id)
        if not dataset:
            return create_response(404, {"error": "Dataset not found"})

        dataset.delete()

        return create_response(200, {"message": "Dataset deleted successfully"})
    except Exception as e:
        return create_response(500, {"error": f"Error deleting dataset: {str(e)}"})
