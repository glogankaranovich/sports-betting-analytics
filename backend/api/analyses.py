"""
Analysis API handler
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict

import boto3

from api.utils import BaseAPIHandler, decimal_to_float


class AnalysesHandler(BaseAPIHandler):
    """Handler for analysis endpoints"""

    def route_request(
        self,
        http_method: str,
        path: str,
        query_params: Dict[str, str],
        path_params: Dict[str, str],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route analysis-related requests"""
        if path == "/analyses" and http_method == "GET":
            return self.get_analyses(query_params)
        elif path == "/top-analysis" and http_method == "GET":
            return self.get_top_analysis(query_params)
        else:
            return self.error_response("Endpoint not found", 404)

    def get_analyses(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get ML analyses using GSI sorted by confidence"""
        try:
            sport = query_params.get("sport", "basketball_nba")
            model = query_params.get("model")
            bookmaker = query_params.get("bookmaker")
            analysis_type = query_params.get("type", "game")
            fetch_all = query_params.get("fetch_all", "false").lower() == "true"

            if not bookmaker or not model:
                return self.error_response("Both bookmaker and model are required")

            limit = 10000 if fetch_all else int(query_params.get("limit", "20"))
            last_evaluated_key_str = query_params.get("lastEvaluatedKey")

            last_evaluated_key = None
            if last_evaluated_key_str and not fetch_all:
                try:
                    last_evaluated_key = json.loads(last_evaluated_key_str)
                except Exception:
                    pass

            analysis_pk = f"ANALYSIS#{sport}#{bookmaker}#{model}#{analysis_type}"
            three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat()

            query_kwargs = {
                "IndexName": "AnalysisTimeGSI",
                "KeyConditionExpression": boto3.dynamodb.conditions.Key(
                    "analysis_time_pk"
                ).eq(analysis_pk)
                & boto3.dynamodb.conditions.Key("commence_time").gte(three_hours_ago),
                "ScanIndexForward": False,
                "Limit": limit,
            }

            if last_evaluated_key and not fetch_all:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_kwargs)
            items = response.get("Items", [])

            analyses = []
            for item in items:
                analysis = {
                    "game_id": item.get("game_id"),
                    "model": item.get("model"),
                    "analysis_type": item.get("analysis_type"),
                    "sport": item.get("sport"),
                    "bookmaker": item.get("bookmaker"),
                    "prediction": item.get("prediction"),
                    "confidence": float(item.get("confidence", 0)),
                    "reasoning": item.get("reasoning"),
                    "home_team": item.get("home_team"),
                    "away_team": item.get("away_team"),
                    "created_at": item.get("created_at"),
                    "commence_time": item.get("commence_time"),
                    "roi": item.get("roi"),
                    "risk_level": item.get("risk_level"),
                }

                if item.get("player_name"):
                    analysis["player_name"] = item.get("player_name")
                if item.get("market_key"):
                    analysis["market_key"] = item.get("market_key")

                analyses.append(analysis)

            analyses = decimal_to_float(analyses)

            result = {
                "analyses": analyses,
                "count": len(analyses),
                "sport": sport,
                "model_filter": model,
                "bookmaker_filter": bookmaker,
            }

            if not fetch_all and response.get("LastEvaluatedKey"):
                result["lastEvaluatedKey"] = json.dumps(response["LastEvaluatedKey"])

            return self.success_response(result)

        except Exception as e:
            return self.error_response(f"Error fetching analyses: {str(e)}", 500)

    def get_top_analysis(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get single top analysis with highest confidence across all models"""
        try:
            sport = query_params.get("sport", "basketball_nba")
            bookmaker = query_params.get("bookmaker", "fanduel")
            current_time = datetime.utcnow().isoformat()

            all_analyses = []
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
            analysis_types = ["game", "prop"]

            for model in models:
                for analysis_type in analysis_types:
                    analysis_pk = f"ANALYSIS#{sport}#{bookmaker}#{model}#{analysis_type}"
                    response = self.table.query(
                        IndexName="AnalysisTimeGSI",
                        KeyConditionExpression=boto3.dynamodb.conditions.Key(
                            "analysis_time_pk"
                        ).eq(analysis_pk)
                        & boto3.dynamodb.conditions.Key("commence_time").gte(current_time),
                        ScanIndexForward=False,
                        Limit=10,
                    )
                    all_analyses.extend(response.get("Items", []))

            if not all_analyses:
                return self.success_response(
                    {"top_analysis": None, "sport": sport, "bookmaker": bookmaker}
                )

            all_analyses.sort(key=lambda x: float(x.get("confidence", 0)), reverse=True)
            top = all_analyses[0]

            top_analysis = {
                "game_id": top.get("game_id"),
                "model": top.get("model"),
                "analysis_type": top.get("analysis_type"),
                "sport": top.get("sport"),
                "bookmaker": top.get("bookmaker"),
                "prediction": top.get("prediction"),
                "confidence": float(top.get("confidence", 0)),
                "reasoning": top.get("reasoning"),
                "home_team": top.get("home_team"),
                "away_team": top.get("away_team"),
                "commence_time": top.get("commence_time"),
            }

            if top.get("player_name"):
                top_analysis["player_name"] = top.get("player_name")
            if top.get("market_key"):
                top_analysis["market_key"] = top.get("market_key")

            return self.success_response(
                {
                    "top_analysis": decimal_to_float(top_analysis),
                    "sport": sport,
                    "bookmaker": bookmaker,
                }
            )

        except Exception as e:
            return self.error_response(f"Error fetching top analysis: {str(e)}", 500)


# Lambda handler entry point
handler = AnalysesHandler()
lambda_handler = handler.lambda_handler
