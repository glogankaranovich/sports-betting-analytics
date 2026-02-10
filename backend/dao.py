"""
Database Access Object for sports betting data
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import boto3


class BettingDAO:
    def __init__(self):
        import os

        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(
            os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
        )

    def get_game_ids_from_db(self, sport: str) -> List[str]:
        """Get unique game IDs for a sport (past 24 hours + next 7 days, latest odds only)"""
        try:
            # Get current time, 24 hours ago, and 7 days from now
            now = datetime.utcnow()
            day_ago = now - timedelta(days=1)
            week_from_now = now + timedelta(days=7)

            game_ids = set()
            last_evaluated_key = None

            while True:
                query_params = {
                    "IndexName": "ActiveBetsIndexV2",
                    "KeyConditionExpression": "active_bet_pk = :active_bet_pk AND commence_time BETWEEN :start_time AND :end_time",
                    "FilterExpression": "attribute_exists(latest)",
                    "ExpressionAttributeValues": {
                        ":active_bet_pk": f"GAME#{sport}",
                        ":start_time": day_ago.isoformat() + "Z",
                        ":end_time": week_from_now.isoformat() + "Z",
                    },
                    "ProjectionExpression": "pk",
                }

                if last_evaluated_key:
                    query_params["ExclusiveStartKey"] = last_evaluated_key

                response = self.table.query(**query_params)

                # Extract unique game IDs from pk (format: GAME#{game_id})
                for item in response["Items"]:
                    game_id = item["pk"].split("#")[1]
                    game_ids.add(game_id)

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break

            return list(game_ids)
        except Exception as e:
            print(
                f"Error getting game IDs from ActiveBetsIndexV2 for {sport}: {str(e)}"
            )
            return []

    def get_prop_ids_from_db(self, sport: str) -> List[str]:
        """Get unique prop IDs for a sport (past 24 hours + next 7 days, latest odds only)"""
        try:
            # Get current time, 24 hours ago, and 7 days from now
            now = datetime.utcnow()
            day_ago = now - timedelta(days=1)
            week_from_now = now + timedelta(days=7)

            prop_ids = set()
            last_evaluated_key = None

            while True:
                query_params = {
                    "IndexName": "ActiveBetsIndexV2",
                    "KeyConditionExpression": "active_bet_pk = :active_bet_pk AND commence_time BETWEEN :start_time AND :end_time",
                    "FilterExpression": "attribute_exists(latest)",
                    "ExpressionAttributeValues": {
                        ":active_bet_pk": f"PROP#{sport}",
                        ":start_time": day_ago.isoformat() + "Z",
                        ":end_time": week_from_now.isoformat() + "Z",
                    },
                    "ProjectionExpression": "pk",
                }

                if last_evaluated_key:
                    query_params["ExclusiveStartKey"] = last_evaluated_key

                response = self.table.query(**query_params)

                # Extract unique prop IDs from pk (format: PROP#{event_id}#{player_name})
                for item in response["Items"]:
                    pk_parts = item["pk"].split("#")
                    if len(pk_parts) >= 3:  # PROP#{event_id}#{player_name}
                        prop_id = f"{pk_parts[1]}#{pk_parts[2]}"  # event_id#player_name
                        prop_ids.add(prop_id)

                last_evaluated_key = response.get("LastEvaluatedKey")
                if not last_evaluated_key:
                    break

            return list(prop_ids)
        except Exception as e:
            print(
                f"Error getting prop IDs from ActiveBetsIndexV2 for {sport}: {str(e)}"
            )
            return []

    def get_prop_data(self, prop_id: str) -> List[Dict]:
        """Get individual prop records for a prop ID"""
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": f"PROP#{prop_id}"},
            )

            prop_records = []
            for item in response["Items"]:
                prop_records.append(
                    {
                        "player_name": item.get("player_name"),
                        "market_key": item.get("market_key"),
                        "event_id": item.get("event_id"),
                        "sport": item.get("sport"),
                        "commence_time": item.get("commence_time"),
                        "bookmaker": item.get("bookmaker"),
                        "outcome": item.get("outcome"),
                        "point": item.get("point"),
                        "price": item.get("price"),
                    }
                )

            return prop_records
        except Exception as e:
            print(f"Error getting prop data for {prop_id}: {str(e)}")
            return []
        except Exception as e:
            print(f"Error getting prop data for {prop_id}: {str(e)}")
            return None

    def get_game_bet_records(self, game_id: str) -> List[Dict]:
        """Get individual game bet records for a game ID"""
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": f"GAME#{game_id}"},
                FilterExpression="attribute_exists(latest)",  # Only get LATEST records
            )
            return response["Items"]
        except Exception as e:
            print(f"Error getting game bet records for {game_id}: {str(e)}")
            return []

    def get_game_data(self, game_id: str) -> Optional[Dict]:
        """Get complete game data including odds from all bookmakers"""
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": f"GAME#{game_id}"},
            )

            if not response["Items"]:
                return None

            # Build game data structure
            game_data = None
            bookmakers = []

            for item in response["Items"]:
                if not game_data:
                    game_data = {
                        "game_id": game_id,
                        "sport": item.get("sport"),
                        "home_team": item.get("home_team"),
                        "away_team": item.get("away_team"),
                        "commence_time": item.get("commence_time"),
                        "bookmakers": [],
                    }

                # Add bookmaker data
                bookmakers.append(
                    {
                        "bookmaker": item.get("sk", "").split("#")[0],
                        "market_key": item.get("sk", "").split("#")[1]
                        if "#" in item.get("sk", "")
                        else "",
                        "outcomes": item.get("outcomes", []),
                    }
                )

            if game_data:
                game_data["bookmakers"] = bookmakers

            return game_data
        except Exception as e:
            print(f"Error getting game data for {game_id}: {str(e)}")
            return None

    def get_game_analysis(
        self,
        sport: str,
        bookmaker: str = "fanduel",
        limit: int = 20,
        last_evaluated_key: Dict = None,
    ) -> Dict:
        """Get active game analysis for a specific sport using sparse index"""
        try:
            current_time = datetime.utcnow().isoformat()

            query_params = {
                "IndexName": "ActiveAnalysisIndexV2",
                "KeyConditionExpression": "active_analysis_pk = :active_analysis_pk AND commence_time >= :current_time",
                "ExpressionAttributeValues": {
                    ":active_analysis_pk": f"GAME#{sport}#{bookmaker}",
                    ":current_time": current_time,
                },
                "Limit": limit,
            }

            if last_evaluated_key:
                query_params["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_params)

            analysis = []
            for item in response.get("Items", []):
                analysis.append(
                    {
                        "pk": item.get("pk"),
                        "sk": item.get("sk"),
                        "game_id": item.get("game_id", ""),
                        "sport": item.get("sport", ""),
                        "home_team": item.get("home_team", ""),
                        "away_team": item.get("away_team", ""),
                        "commence_time": item.get("commence_time", ""),
                        "home_win_probability": float(
                            item.get("home_win_probability", 0)
                        ),
                        "away_win_probability": float(
                            item.get("away_win_probability", 0)
                        ),
                        "confidence_score": float(item.get("confidence_score", 0)),
                        "model": item.get("model", ""),
                        "status": item.get("status", ""),
                        "value_bets": item.get("value_bets", []),
                    }
                )

            return {
                "items": analysis,
                "lastEvaluatedKey": response.get("LastEvaluatedKey"),
            }

        except Exception as e:
            print(f"Error getting game analysis for {sport}: {str(e)}")
            return {"items": [], "lastEvaluatedKey": None}

    def get_prop_analysis(
        self, sport: str, limit: int = 20, last_evaluated_key: Dict = None
    ) -> Dict:
        """Get active prop analysis for a specific sport using sparse index"""
        try:
            current_time = datetime.utcnow().isoformat()

            query_params = {
                "IndexName": "ActiveAnalysisIndexV2",
                "KeyConditionExpression": "active_analysis_pk = :active_analysis_pk AND commence_time >= :current_time",
                "ExpressionAttributeValues": {
                    ":active_analysis_pk": f"PROP#{sport}",
                    ":current_time": current_time,
                },
                "Limit": limit,
            }

            if last_evaluated_key:
                query_params["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_params)

            analysis = []
            for item in response.get("Items", []):
                analysis.append(
                    {
                        "pk": item.get("pk"),
                        "sk": item.get("sk"),
                        "event_id": item.get("event_id", ""),
                        "player_name": item.get("player_name", ""),
                        "prop_type": item.get("prop_type", ""),
                        "sport": item.get("sport", ""),
                        "commence_time": item.get("commence_time", ""),
                        "predicted_value": float(item.get("predicted_value", 0)),
                        "over_probability": float(item.get("over_probability", 0)),
                        "under_probability": float(item.get("under_probability", 0)),
                        "confidence_score": float(item.get("confidence_score", 0)),
                        "model": item.get("model", ""),
                    }
                )

            return {
                "items": analysis,
                "lastEvaluatedKey": response.get("LastEvaluatedKey"),
            }

        except Exception as e:
            print(f"Error getting prop analysis for {sport}: {str(e)}")
            return {"items": [], "lastEvaluatedKey": None}
