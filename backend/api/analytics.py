"""
Analytics API handler (model performance, comparison, rankings)
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict

from boto3.dynamodb.conditions import Key

from api.utils import BaseAPIHandler, table, table_name, decimal_to_float
from constants import SYSTEM_MODELS


class AnalyticsHandler(BaseAPIHandler):
    """Handler for analytics endpoints"""

    def route_request(
        self,
        http_method: str,
        path: str,
        query_params: Dict[str, str],
        path_params: Dict[str, str],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route analytics requests"""
        if path == "/analytics":
            return self.get_analytics(query_params)
        elif path == "/model-performance":
            return self.get_model_performance(query_params)
        elif path == "/model-comparison":
            return self.get_model_comparison(query_params)
        elif path == "/model-rankings":
            return self.get_model_rankings(query_params)
        else:
            return self.error_response("Endpoint not found", 404)

    def get_analytics(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get model analytics data from DynamoDB cache"""
        try:
            metric_type = query_params.get("type", "summary")
            days = int(query_params.get("days", 90))

            # Handle weights separately (not cached)
            if metric_type == "weights":
                from ml.dynamic_weighting import DynamicModelWeighting

                weighting = DynamicModelWeighting()
                sport = query_params.get("sport", "basketball_nba")
                bet_type = query_params.get("bet_type", "game")

                weights = weighting.get_model_weights(sport, bet_type, models=SYSTEM_MODELS)
                model_metrics = {}
                for model_name in SYSTEM_MODELS:
                    accuracy = weighting.get_recent_accuracy(model_name, sport, bet_type)
                    brier = weighting.get_recent_brier_score(model_name, sport, bet_type)
                    model_metrics[model_name] = {"weight": weights[model_name], "recent_accuracy": accuracy, "recent_brier_score": brier}

                data = {"sport": sport, "bet_type": bet_type, "lookback_days": weighting.lookback_days, "model_weights": model_metrics}
                return self.success_response(decimal_to_float(data))

            model = query_params.get("model")

            # Build partition key for query
            if metric_type == "summary":
                pk = "ANALYTICS#summary"
            elif metric_type in ["by_sport", "by_bet_type", "confidence", "over_time", "recent_predictions"]:
                if not model:
                    return self.error_response(f"model parameter required for {metric_type}")
                if model == "all" and metric_type == "by_bet_type":
                    from model_analytics import ModelAnalytics
                    analytics = ModelAnalytics(table_name)
                    data = analytics.get_model_performance_by_bet_type(days=days)
                    return self.success_response(decimal_to_float(data))
                pk = f"ANALYTICS#{metric_type}"
            else:
                return self.error_response(f"Unknown metric type: {metric_type}")

            # Query DynamoDB for cached analytics
            if model and metric_type != "summary":
                response = table.query(KeyConditionExpression="pk = :pk AND begins_with(sk, :sk)", ExpressionAttributeValues={":pk": pk, ":sk": model}, ScanIndexForward=False, Limit=1)
            else:
                response = table.query(KeyConditionExpression="pk = :pk", ExpressionAttributeValues={":pk": pk}, ScanIndexForward=False, Limit=1)

            if not response.get("Items"):
                # Cache miss - compute on-demand
                from model_analytics import ModelAnalytics
                analytics = ModelAnalytics(table_name)

                if metric_type == "summary":
                    data = analytics.get_model_performance_summary(days=days)
                elif metric_type == "by_sport":
                    data = analytics.get_model_performance_by_sport(model=model, days=days)
                elif metric_type == "by_bet_type":
                    data = analytics.get_model_performance_by_bet_type(model=model, days=days)
                elif metric_type == "confidence":
                    data = analytics.get_model_confidence_analysis(model=model, days=days)
                elif metric_type == "over_time":
                    data = analytics.get_performance_over_time(model=model, days=days)
                elif metric_type == "recent_predictions":
                    limit = int(query_params.get("limit", 20))
                    data = analytics.get_recent_predictions(model=model, limit=limit)
                else:
                    return self.error_response(f"Unknown metric type: {metric_type}")

                return self.success_response(decimal_to_float(data))

            data = response["Items"][0].get("data", {})
            return self.success_response(decimal_to_float(data))

        except Exception as e:
            return self.error_response(str(e), 500)

    def get_model_performance(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get model performance metrics"""
        try:
            from model_performance import ModelPerformanceTracker

            tracker = ModelPerformanceTracker(table_name)
            sport = query_params.get("sport", "basketball_nba")
            model = query_params.get("model")
            days = int(query_params.get("days", 30))

            if model:
                performance = tracker.get_model_performance(model, sport, days)
                return self.success_response({"model": model, "sport": sport, "days": days, "performance": decimal_to_float(performance)})
            else:
                performance = tracker.get_all_models_performance(sport, days)
                return self.success_response({"sport": sport, "days": days, "models": decimal_to_float(performance)})

        except Exception as e:
            return self.error_response(f"Error fetching model performance: {str(e)}", 500)

    def get_model_comparison(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get model comparison with original vs inverse performance"""
        try:
            from api_middleware import check_feature_access
            from feature_flags import get_user_limits

            sport = query_params.get("sport", "basketball_nba")
            days = int(query_params.get("days", 90))
            user_id = query_params.get("user_id")

            # Handle "all sports" request
            if sport == "all":
                # Try combined cache first
                cache_key = f"MODEL_COMPARISON#all#{days}"
                try:
                    cache_response = table.get_item(Key={"pk": "CACHE", "sk": cache_key})
                    if "Item" in cache_response:
                        all_models = cache_response["Item"]["data"]
                        
                        if user_id:
                            limits = get_user_limits(user_id)
                            if not limits.get("benny_ai", False):
                                all_models = [m for m in all_models if m.get("model") != "benny"]
                        else:
                            all_models = [m for m in all_models if m.get("model") != "benny"]
                        
                        return self.success_response({"sport": "all", "days": days, "models": all_models, "cached": True})
                except Exception as e:
                    print(f"Error fetching combined cache: {e}")
                
                # Fallback: fetch individual sport caches
                all_sports = ["basketball_nba", "americanfootball_nfl", "baseball_mlb", "icehockey_nhl", "soccer_epl"]
                all_models = []

                for s in all_sports:
                    cache_key = f"MODEL_COMPARISON#{s}#{days}"
                    try:
                        cache_response = table.get_item(Key={"pk": "CACHE", "sk": cache_key})
                        if "Item" in cache_response:
                            cached_items = cache_response["Item"]["data"]
                            for item in cached_items:
                                if "sport" not in item:
                                    item["sport"] = s
                            all_models.extend(cached_items)
                            continue
                    except Exception:
                        pass

                    cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat() if days < 9999 else "2000-01-01T00:00:00"
                    for model in SYSTEM_MODELS:
                        if model == "benny" and not user_id:
                            continue
                        model_data = _get_model_comparison_data(model, s, cutoff_time, is_user_model=False)
                        if model_data:
                            all_models.extend(model_data)

                if user_id:
                    limits = get_user_limits(user_id)
                    if not limits.get("benny_ai", False):
                        all_models = [m for m in all_models if m.get("model") != "benny"]
                else:
                    all_models = [m for m in all_models if m.get("model") != "benny"]

                all_models.sort(key=lambda x: max(x["original_accuracy"], x["inverse_accuracy"]), reverse=True)
                return self.success_response({"sport": "all", "days": days, "models": all_models, "cached": False})

            # Try cache first
            cache_key = f"MODEL_COMPARISON#{sport}#{days}"
            try:
                cache_response = table.get_item(Key={"pk": "CACHE", "sk": cache_key})
                if "Item" in cache_response:
                    cached_data = cache_response["Item"]["data"]

                    if user_id:
                        limits = get_user_limits(user_id)
                        if not limits.get("benny_ai", False):
                            cached_data = [m for m in cached_data if m.get("model") != "benny"]
                    else:
                        cached_data = [m for m in cached_data if m.get("model") != "benny"]

                    if user_id:
                        access_check = check_feature_access(user_id, "user_models")
                        if access_check["allowed"]:
                            from user_models import UserModel

                            cutoff_time = "2000-01-01T00:00:00" if days >= 9999 else (datetime.utcnow() - timedelta(days=days)).isoformat()
                            user_models = UserModel.list_by_user(user_id)
                            for user_model in user_models:
                                if user_model.sport == sport and user_model.status == "active":
                                    model_data = _get_model_comparison_data(user_model.model_id, sport, cutoff_time, is_user_model=True, model_name=user_model.name)
                                    if model_data:
                                        cached_data.extend(model_data)

                        cached_data.sort(key=lambda x: max(x["original_accuracy"], x["inverse_accuracy"]), reverse=True)

                    return self.success_response({"sport": sport, "days": days, "models": cached_data, "cached": True, "computed_at": cache_response["Item"].get("computed_at")})
            except Exception:
                pass

            # Compute on-demand
            cutoff_time = "2000-01-01T00:00:00" if days >= 9999 else (datetime.utcnow() - timedelta(days=days)).isoformat()
            comparison = []

            allowed_models = list(SYSTEM_MODELS)
            if user_id:
                limits = get_user_limits(user_id)
                if not limits.get("benny_ai", False):
                    allowed_models = [m for m in allowed_models if m != "benny"]
            else:
                allowed_models = [m for m in allowed_models if m != "benny"]

            for model in allowed_models:
                model_data = _get_model_comparison_data(model, sport, cutoff_time, is_user_model=False)
                if model_data:
                    comparison.extend(model_data)

            if user_id:
                from user_models import UserModel
                user_models = UserModel.list_by_user(user_id)
                for user_model in user_models:
                    if user_model.sport == sport and user_model.status == "active":
                        model_data = _get_model_comparison_data(user_model.model_id, sport, cutoff_time, is_user_model=True, model_name=user_model.name)
                        if model_data:
                            comparison.extend(model_data)

            comparison.sort(key=lambda x: max(x["original_accuracy"], x["inverse_accuracy"]), reverse=True)

            return self.success_response({
                "sport": sport,
                "days": days,
                "models": comparison,
                "summary": {
                    "total_models": len(comparison),
                    "inverse_recommended": sum(1 for m in comparison if m["recommendation"] == "INVERSE"),
                    "original_recommended": sum(1 for m in comparison if m["recommendation"] == "ORIGINAL"),
                    "avoid": sum(1 for m in comparison if m["recommendation"] == "AVOID"),
                },
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self.error_response(f"Error fetching model comparison: {str(e)}", 500)

    def get_model_rankings(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get model rankings by ROI and profitability metrics"""
        try:
            sport = query_params.get("sport", "basketball_nba")
            days = int(query_params.get("days", 30))
            user_id = query_params.get("user_id")
            mode = query_params.get("mode", "both")

            cutoff_time = (datetime.utcnow() - timedelta(days=days)).isoformat()
            rankings = []

            for model in SYSTEM_MODELS:
                model_data = _calculate_model_roi(model, sport, cutoff_time, is_user_model=False, mode=mode)
                if model_data:
                    rankings.extend(model_data)

            if user_id:
                from user_models import UserModel
                user_models = UserModel.list_by_user(user_id)
                for user_model in user_models:
                    if user_model.sport == sport and user_model.status == "active":
                        model_data = _calculate_model_roi(user_model.model_id, sport, cutoff_time, is_user_model=True, model_name=user_model.name, mode=mode)
                        if model_data:
                            rankings.extend(model_data)

            rankings.sort(key=lambda x: x["roi"], reverse=True)

            return self.success_response({
                "sport": sport,
                "days": days,
                "mode": mode,
                "rankings": rankings,
                "summary": {
                    "total_models": len(rankings),
                    "profitable": sum(1 for r in rankings if r["roi"] > 0),
                    "unprofitable": sum(1 for r in rankings if r["roi"] < 0),
                    "avg_roi": round(sum(r["roi"] for r in rankings) / len(rankings), 3) if rankings else 0,
                },
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return self.error_response(f"Error fetching rankings: {str(e)}", 500)


def _calculate_model_roi(model_id: str, sport: str, cutoff_time: str, is_user_model: bool = False, model_name: str = None, mode: str = "both") -> list:
    """Calculate ROI metrics for a model"""
    try:
        results = []
        modes_to_calc = []
        if mode in ["original", "both"]:
            modes_to_calc.append(("original", ""))
        if mode in ["inverse", "both"]:
            modes_to_calc.append(("inverse", "#inverse"))

        for mode_name, pk_suffix in modes_to_calc:
            pk = f"VERIFIED#{model_id}#{sport}#game{pk_suffix}"
            response = table.query(IndexName="VerifiedAnalysisGSI", KeyConditionExpression=Key("verified_analysis_pk").eq(pk) & Key("verified_analysis_sk").gte(cutoff_time), Limit=1000)
            items = response.get("Items", [])

            if not items:
                continue

            total_bets = len(items)
            wins = sum(1 for item in items if item.get("analysis_correct"))
            losses = total_bets - wins
            win_rate = wins / total_bets if total_bets > 0 else 0

            total_profit = 0
            total_wagered = total_bets * 100
            odds_sum = 0
            odds_count = 0

            for item in items:
                outcomes = item.get("outcomes", [])
                if outcomes and len(outcomes) > 0:
                    odds = float(outcomes[0].get("price", 0))
                    odds_sum += odds
                    odds_count += 1

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

            if total_bets > 1:
                avg_return = total_profit / total_bets
                variance = sum(((100 if item.get("analysis_correct") else -100) - avg_return) ** 2 for item in items) / (total_bets - 1)
                std_dev = variance**0.5
                sharpe = avg_return / std_dev if std_dev > 0 else 0
            else:
                sharpe = 0

            results.append({"model": model_name or model_id, "model_id": model_id, "mode": mode_name, "is_user_model": is_user_model, "total_bets": total_bets, "wins": wins, "losses": losses, "win_rate": round(win_rate, 3), "avg_odds": round(avg_odds, 0), "profit": round(total_profit, 2), "roi": round(roi, 3), "sharpe_ratio": round(sharpe, 3)})

        return results

    except Exception as e:
        print(f"Error calculating ROI for {model_id}: {e}")
        return []


def _get_model_comparison_data(model_id: str, sport: str, cutoff_time: str, is_user_model: bool = False, model_name: str = None) -> list:
    """Get comparison data for a single model"""
    try:
        results = []

        for bet_type in ["game", "prop"]:
            original_pk = f"VERIFIED#{model_id}#{sport}#{bet_type}"
            original_response = table.query(IndexName="VerifiedAnalysisGSI", KeyConditionExpression=Key("verified_analysis_pk").eq(original_pk) & Key("verified_analysis_sk").gte(cutoff_time), Limit=5000)
            original_items = original_response.get("Items", [])

            inverse_pk = f"{original_pk}#inverse"
            inverse_response = table.query(IndexName="VerifiedAnalysisGSI", KeyConditionExpression=Key("verified_analysis_pk").eq(inverse_pk) & Key("verified_analysis_sk").gte(cutoff_time), Limit=5000)
            inverse_items = inverse_response.get("Items", [])

            if not original_items:
                continue

            original_total = len(original_items)
            original_correct = sum(1 for item in original_items if item.get("analysis_correct"))
            original_accuracy = original_correct / original_total if original_total > 0 else 0

            inverse_total = len(inverse_items)
            inverse_correct = sum(1 for item in inverse_items if item.get("analysis_correct"))
            inverse_accuracy = inverse_correct / inverse_total if inverse_total > 0 else 0

            if inverse_accuracy > original_accuracy and inverse_accuracy > 0.5:
                recommendation = "INVERSE"
            elif original_accuracy > 0.5:
                recommendation = "ORIGINAL"
            else:
                recommendation = "AVOID"

            results.append({"model": model_name or model_id, "model_id": model_id, "sport": sport, "bet_type": bet_type, "is_user_model": is_user_model, "sample_size": original_total, "original_accuracy": round(original_accuracy, 3), "original_correct": original_correct, "original_total": original_total, "inverse_accuracy": round(inverse_accuracy, 3), "inverse_correct": inverse_correct, "inverse_total": inverse_total, "recommendation": recommendation, "accuracy_diff": round(inverse_accuracy - original_accuracy, 3)})

        return results

    except Exception as e:
        print(f"Error getting comparison data for {model_id}: {e}")
        return []


# Lambda handler entry point
handler = AnalyticsHandler()
lambda_handler = handler.lambda_handler
