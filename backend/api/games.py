"""
Games and odds API handler
"""

import json
from datetime import datetime, timedelta
from typing import Any, Dict

import boto3

from api.utils import BaseAPIHandler, decimal_to_float


class GamesHandler(BaseAPIHandler):
    """Handler for games and odds endpoints"""

    def route_request(
        self,
        http_method: str,
        path: str,
        query_params: Dict[str, str],
        path_params: Dict[str, str],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route games-related requests"""
        if path == "/games" and http_method == "GET":
            return self.get_games(query_params)
        elif path == "/player-props" and http_method == "GET":
            return self.get_player_props(query_params)
        elif path == "/sports" and http_method == "GET":
            return self.get_sports()
        elif path == "/bookmakers" and http_method == "GET":
            return self.get_bookmakers()
        else:
            return self.error_response("Endpoint not found", 404)

    def get_games(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get all games with latest odds"""
        sport = query_params.get("sport")
        if not sport:
            return self.error_response("sport parameter is required")

        bookmaker = query_params.get("bookmaker")
        fetch_all = query_params.get("fetch_all", "false").lower() == "true"
        limit = 10000 if fetch_all else int(query_params.get("limit", "20"))
        last_evaluated_key = query_params.get("lastEvaluatedKey")

        display_bookmakers = {"fanatics", "fanduel", "draftkings", "betmgm"}

        try:
            exclusive_start_key = None
            if last_evaluated_key and not fetch_all:
                try:
                    exclusive_start_key = json.loads(last_evaluated_key)
                except Exception:
                    pass

            three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat()

            filter_expr = boto3.dynamodb.conditions.Attr("latest").eq(True)
            if bookmaker:
                filter_expr = filter_expr & boto3.dynamodb.conditions.Attr(
                    "sk"
                ).begins_with(f"{bookmaker}#")

            query_kwargs = {
                "IndexName": "ActiveBetsIndexV2",
                "KeyConditionExpression": boto3.dynamodb.conditions.Key("active_bet_pk").eq(
                    f"GAME#{sport}"
                )
                & boto3.dynamodb.conditions.Key("commence_time").gte(three_hours_ago),
                "FilterExpression": filter_expr,
                "Limit": limit * 10,
            }

            if exclusive_start_key:
                query_kwargs["ExclusiveStartKey"] = exclusive_start_key

            response = self.table.query(**query_kwargs)
            odds_items = response.get("Items", [])

            # Group odds by game_id
            games_dict = {}
            for item in odds_items:
                game_id = item["pk"][5:]  # Remove 'GAME#' prefix
                if game_id not in games_dict:
                    games_dict[game_id] = {
                        "game_id": game_id,
                        "sport": item["sport"],
                        "home_team": item["home_team"],
                        "away_team": item["away_team"],
                        "commence_time": item["commence_time"],
                        "updated_at": item["updated_at"],
                        "odds": {},
                    }

                if "#" in item["sk"]:
                    parts = item["sk"].split("#")
                    bookmaker_name = parts[0]
                    market = parts[1]

                    allowed_bookmakers = {bookmaker} if bookmaker else display_bookmakers
                    if bookmaker_name in allowed_bookmakers:
                        if bookmaker_name not in games_dict[game_id]["odds"]:
                            games_dict[game_id]["odds"][bookmaker_name] = {}
                        games_dict[game_id]["odds"][bookmaker_name][market] = item["outcomes"]

            games = list(games_dict.values())
            if not fetch_all:
                games = games[:limit]
            games = decimal_to_float(games)

            result = {"games": games, "count": len(games), "sport_filter": sport}
            if not fetch_all and "LastEvaluatedKey" in response:
                result["lastEvaluatedKey"] = json.dumps(response["LastEvaluatedKey"])

            return self.success_response(result)
        except Exception as e:
            return self.error_response(f"Error fetching games: {str(e)}", 500)

    def get_player_props(self, query_params: Dict[str, str]) -> Dict[str, Any]:
        """Get player props with optional filtering"""
        sport = query_params.get("sport")
        if not sport:
            return self.error_response("sport parameter is required")

        bookmaker = query_params.get("bookmaker")
        prop_type = query_params.get("prop_type")
        fetch_all = query_params.get("fetch_all", "false").lower() == "true"
        limit = 10000 if fetch_all else int(query_params.get("limit", "20"))

        display_bookmakers = ["fanatics", "fanduel", "draftkings", "betmgm"]

        try:
            three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat()

            filter_expressions = [boto3.dynamodb.conditions.Attr("latest").eq(True)]

            if bookmaker:
                filter_expressions.append(
                    boto3.dynamodb.conditions.Attr("bookmaker").eq(bookmaker)
                )
            else:
                bookmaker_filter = boto3.dynamodb.conditions.Attr("bookmaker").eq(display_bookmakers[0])
                for bm in display_bookmakers[1:]:
                    bookmaker_filter = bookmaker_filter | boto3.dynamodb.conditions.Attr("bookmaker").eq(bm)
                filter_expressions.append(bookmaker_filter)

            if prop_type:
                filter_expressions.append(
                    boto3.dynamodb.conditions.Attr("market_key").eq(prop_type)
                )

            filter_expression = filter_expressions[0]
            for expr in filter_expressions[1:]:
                filter_expression = filter_expression & expr

            props = []
            current_key = None
            max_iterations = 10

            while len(props) < limit and max_iterations > 0:
                max_iterations -= 1
                query_kwargs = {
                    "IndexName": "ActiveBetsIndexV2",
                    "KeyConditionExpression": boto3.dynamodb.conditions.Key(
                        "active_bet_pk"
                    ).eq(f"PROP#{sport}")
                    & boto3.dynamodb.conditions.Key("commence_time").gte(three_hours_ago),
                    "FilterExpression": filter_expression,
                    "Limit": limit * 3,
                }

                if current_key:
                    query_kwargs["ExclusiveStartKey"] = current_key

                response = self.table.query(**query_kwargs)
                batch = response.get("Items", [])
                props.extend(batch)

                current_key = response.get("LastEvaluatedKey")
                if not current_key or (not fetch_all and len(props) >= limit):
                    break

            if not fetch_all:
                props = props[:limit]

            props = decimal_to_float(props)

            result = {
                "props": props,
                "count": len(props),
                "filters": {"sport": sport, "bookmaker": bookmaker, "prop_type": prop_type},
            }

            if current_key and not fetch_all and len(props) >= limit:
                result["lastEvaluatedKey"] = json.dumps(current_key)

            return self.success_response(result)
        except Exception as e:
            return self.error_response(f"Error fetching player props: {str(e)}", 500)

    def get_sports(self) -> Dict[str, Any]:
        """Get list of available sports"""
        try:
            response = self.table.scan(ProjectionExpression="sport")
            sports = set()
            for item in response.get("Items", []):
                if "sport" in item:
                    sports.add(item["sport"])

            return self.success_response({"sports": sorted(list(sports)), "count": len(sports)})
        except Exception as e:
            return self.error_response(f"Error fetching sports: {str(e)}", 500)

    def get_bookmakers(self) -> Dict[str, Any]:
        """Get list of available bookmakers"""
        try:
            response = self.table.scan(ProjectionExpression="bookmaker")
            bookmakers = set()
            for item in response.get("Items", []):
                if "bookmaker" in item:
                    bookmakers.add(item["bookmaker"])

            return self.success_response({"bookmakers": sorted(list(bookmakers))})
        except Exception as e:
            return self.error_response(f"Error fetching bookmakers: {str(e)}", 500)


# Lambda handler entry point
handler = GamesHandler()
lambda_handler = handler.lambda_handler
