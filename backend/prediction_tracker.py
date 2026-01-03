"""
Prediction storage and tracking system - Clean separation of game and prop predictions
"""

import boto3
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from ml.models import OddsAnalyzer


class PredictionTracker:
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.table = self.dynamodb.Table(table_name)
        self.analyzer = OddsAnalyzer()

    def generate_and_store_predictions(self, model: str = "consensus") -> int:
        """Generate both game and prop predictions"""
        game_predictions = self.generate_game_predictions(model=model)
        prop_predictions = self.generate_prop_predictions(model=model)
        return game_predictions + prop_predictions

    def generate_game_predictions(self, model: str = "consensus") -> int:
        """Generate and store game predictions only"""
        # Get all games using new schema
        response = self.table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("pk").begins_with("GAME#")
        )
        games_by_id = {}

        for item in response.get("Items", []):
            pk = item.get("pk", "")
            sk = item.get("sk", "")

            game_id = pk.replace("GAME#", "")
            if not game_id:
                continue

            if game_id not in games_by_id:
                games_by_id[game_id] = {
                    "game_id": game_id,
                    "sport": item.get("sport"),
                    "home_team": item.get("home_team"),
                    "away_team": item.get("away_team"),
                    "commence_time": item.get("commence_time"),
                    "odds": {},
                }

            # Parse sk to get bookmaker and market
            sk_parts = sk.split("#")
            if len(sk_parts) >= 2:
                bookmaker = sk_parts[0]
                market = sk_parts[1]

                if bookmaker not in games_by_id[game_id]["odds"]:
                    games_by_id[game_id]["odds"][bookmaker] = {}

                games_by_id[game_id]["odds"][bookmaker][market] = {
                    "outcomes": item.get("outcomes", [])
                }

        print(f"Found {len(games_by_id)} unique games")

        # Generate and store game predictions
        predictions_stored = 0
        timestamp = datetime.utcnow().isoformat()

        for game_data in games_by_id.values():
            try:
                print(
                    f"Processing game: {game_data['home_team']} vs {game_data['away_team']}"
                )
                prediction = self.analyzer.analyze_game(game_data)

                # Determine if prediction is active (game hasn't started)
                commence_time = game_data["commence_time"]
                is_active = commence_time > timestamp
                prediction_status = "ACTIVE" if is_active else "HISTORICAL"

                self.table.put_item(
                    Item={
                        "pk": f"PRED#GAME#{game_data['game_id']}",
                        "sk": f"PREDICTION#{model}",
                        "prediction_type": "GAME",  # GSI partition key
                        "game_id": game_data["game_id"],
                        "sport": game_data["sport"],
                        "home_team": game_data["home_team"],
                        "away_team": game_data["away_team"],
                        "commence_time": game_data["commence_time"],  # GSI sort key
                        "model": model,
                        "is_active": is_active,
                        "prediction_status": prediction_status,
                        "created_at": timestamp,
                        "expires_at": commence_time,
                        "home_win_probability": Decimal(
                            str(prediction.home_win_probability)
                        ),
                        "away_win_probability": Decimal(
                            str(prediction.away_win_probability)
                        ),
                        "confidence_score": Decimal(str(prediction.confidence_score)),
                        "value_bets": prediction.value_bets,
                        "predicted_at": timestamp,
                        "status": "pending",
                    }
                )

                predictions_stored += 1
                print(
                    f"Stored game prediction: Home {prediction.home_win_probability}, Away {prediction.away_win_probability}"
                )

            except Exception as e:
                print(f"Error processing game: {e}")
                continue

        return predictions_stored

    def generate_game_predictions_for_sport(
        self, sport: str, model: str = "consensus", limit: int = None
    ) -> int:
        """Generate and store game predictions for specific sport"""
        response = self.table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("pk").begins_with("GAME#")
            & boto3.dynamodb.conditions.Attr("sport").eq(sport)
        )
        games_by_id = {}

        for item in response.get("Items", []):
            pk = item.get("pk", "")
            game_id = pk.replace("GAME#", "")
            if not game_id:
                continue

            if game_id not in games_by_id:
                games_by_id[game_id] = {
                    "game_id": game_id,
                    "sport": item.get("sport"),
                    "home_team": item.get("home_team"),
                    "away_team": item.get("away_team"),
                    "commence_time": item.get("commence_time"),
                    "bookmakers": [],
                }

            games_by_id[game_id]["bookmakers"].append(item)

        timestamp = datetime.utcnow().isoformat()
        predictions_stored = 0

        # Apply limit to number of games before generating predictions
        if limit and limit > 0:
            games_by_id = dict(list(games_by_id.items())[:limit])
            print(f"Limited to {len(games_by_id)} games for prediction generation")

        for game_data in games_by_id.values():
            try:
                print(
                    f"Processing {sport} game: {game_data['home_team']} vs {game_data['away_team']}"
                )
                prediction = self.analyzer.analyze_game(game_data)

                # Determine if prediction is active (game hasn't started)
                commence_time = game_data["commence_time"]
                is_active = commence_time > timestamp
                prediction_status = "ACTIVE" if is_active else "HISTORICAL"

                self.table.put_item(
                    Item={
                        "pk": f"PRED#GAME#{game_data['game_id']}",
                        "sk": f"PREDICTION#{model}",
                        "prediction_type": "GAME",
                        "game_id": game_data["game_id"],
                        "sport": game_data["sport"],
                        "home_team": game_data["home_team"],
                        "away_team": game_data["away_team"],
                        "commence_time": game_data["commence_time"],
                        "model": model,
                        "is_active": is_active,
                        "prediction_status": prediction_status,
                        "created_at": timestamp,
                        "expires_at": commence_time,
                        "home_win_probability": Decimal(
                            str(prediction.home_win_probability)
                        ),
                        "away_win_probability": Decimal(
                            str(prediction.away_win_probability)
                        ),
                        "confidence_score": Decimal(str(prediction.confidence_score)),
                        "value_bets": prediction.value_bets,
                        "predicted_at": timestamp,
                        "status": "pending",
                    }
                )
                predictions_stored += 1

            except Exception as e:
                print(f"Error processing game {game_data['game_id']}: {str(e)}")
                continue

        return predictions_stored

    def generate_prop_predictions_for_sport(
        self, sport: str, model: str = "consensus", limit: int = None
    ) -> int:
        """Generate and store prop predictions for specific sport"""
        response = self.table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("pk").begins_with("PROP#")
            & boto3.dynamodb.conditions.Attr("sport").eq(sport)
        )
        player_props = response.get("Items", [])

        if not player_props:
            print(f"No player props found for {sport}")
            return 0

        # Apply limit to player props before generating predictions
        if limit and limit > 0:
            player_props = player_props[:limit]
            print(
                f"Limited to {len(player_props)} player props for prediction generation"
            )

        prop_predictions = self.analyzer.analyze_player_props(player_props)
        timestamp = datetime.utcnow().isoformat()
        predictions_stored = 0

        for prop_pred in prop_predictions:
            try:
                # Find event_id from the prop data
                event_id = None
                for prop in player_props:
                    if (
                        prop.get("player_name") == prop_pred.player_name
                        and prop.get("market_key") == prop_pred.prop_type
                    ):
                        pk_parts = prop.get("pk", "").split("#")
                        if len(pk_parts) >= 2:
                            event_id = pk_parts[1]
                        break

                # Find commence_time for this prop prediction
                commence_time = None
                for prop in player_props:
                    if (
                        prop.get("player_name") == prop_pred.player_name
                        and prop.get("market_key") == prop_pred.prop_type
                    ):
                        commence_time = prop.get("commence_time")
                        break

                # Determine if prediction is active (game hasn't started)
                is_active = commence_time and commence_time > timestamp
                prediction_status = "ACTIVE" if is_active else "HISTORICAL"

                self.table.put_item(
                    Item={
                        "pk": f"PRED#PROP#{event_id}#{prop_pred.prop_type}#{prop_pred.player_name}",
                        "sk": f"PROP_PREDICTION#{model}",
                        "prediction_type": "PROP",
                        "event_id": event_id,
                        "player_name": prop_pred.player_name,
                        "prop_type": prop_pred.prop_type,
                        "sport": sport,
                        "commence_time": commence_time,
                        "model": model,
                        "is_active": is_active,
                        "prediction_status": prediction_status,
                        "created_at": timestamp,
                        "expires_at": commence_time,
                        "predicted_value": Decimal(str(prop_pred.predicted_value)),
                        "over_probability": Decimal(str(prop_pred.over_probability)),
                        "under_probability": Decimal(str(prop_pred.under_probability)),
                        "confidence_score": Decimal(str(prop_pred.confidence_score)),
                        "predicted_at": timestamp,
                    }
                )
                predictions_stored += 1

            except Exception as e:
                print(
                    f"Error processing prop prediction for {prop_pred.player_name}: {str(e)}"
                )
                continue

        return predictions_stored

    def generate_prop_predictions(self, model: str = "consensus") -> int:
        """Generate and store prop predictions only"""
        # Get all player props
        response = self.table.scan(
            FilterExpression=boto3.dynamodb.conditions.Attr("pk").begins_with("PROP#")
        )

        player_props = response.get("Items", [])
        print(f"Found {len(player_props)} player props")

        if not player_props:
            return 0

        predictions_stored = 0
        timestamp = datetime.utcnow().isoformat()

        try:
            prop_predictions = self.analyzer.analyze_player_props(player_props)

            for prop_pred in prop_predictions:
                # Find the event_id for this prop prediction
                event_id = "unknown"
                for prop in player_props:
                    if (
                        prop.get("player_name") == prop_pred.player_name
                        and prop.get("market_key") == prop_pred.prop_type
                    ):
                        pk_parts = prop.get("pk", "").split("#")
                        if len(pk_parts) >= 2:
                            event_id = pk_parts[1]
                        break

                # Find commence_time for this prop prediction
                commence_time = None
                for prop in player_props:
                    if (
                        prop.get("player_name") == prop_pred.player_name
                        and prop.get("market_key") == prop_pred.prop_type
                    ):
                        commence_time = prop.get("commence_time")
                        break

                # Determine if prediction is active (game hasn't started)
                is_active = commence_time and commence_time > timestamp
                prediction_status = "ACTIVE" if is_active else "HISTORICAL"

                self.table.put_item(
                    Item={
                        "pk": f"PRED#PROP#{event_id}#{prop_pred.prop_type}#{prop_pred.player_name}",
                        "sk": f"PROP_PREDICTION#{model}",
                        "prediction_type": "PROP",  # GSI partition key
                        "event_id": event_id,
                        "player_name": prop_pred.player_name,
                        "prop_type": prop_pred.prop_type,
                        "commence_time": commence_time,  # GSI sort key
                        "model": model,
                        "is_active": is_active,
                        "prediction_status": prediction_status,
                        "created_at": timestamp,
                        "expires_at": commence_time,
                        "predicted_value": Decimal(str(prop_pred.predicted_value)),
                        "over_probability": Decimal(str(prop_pred.over_probability)),
                        "under_probability": Decimal(str(prop_pred.under_probability)),
                        "confidence_score": Decimal(str(prop_pred.confidence_score)),
                        "value_bets": prop_pred.value_bets,
                        "model_version": "consensus_v1",
                        "predicted_at": timestamp,
                        "status": "pending",
                    }
                )
                predictions_stored += 1

            print(f"Stored {predictions_stored} prop predictions")

        except Exception as e:
            print(f"Error generating prop predictions: {e}")

        return predictions_stored

    def get_predictions(self, limit: int = 50) -> List[Dict]:
        """Get active predictions using GSI with time filtering"""
        from datetime import datetime

        predictions = []
        current_time = datetime.utcnow().isoformat()

        # Get game predictions for upcoming games only
        game_response = self.table.query(
            IndexName="ActivePredictionsIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("prediction_type").eq(
                "GAME"
            )
            & boto3.dynamodb.conditions.Key("commence_time").gte(current_time),
            Limit=limit // 2,
        )

        # Get prop predictions for upcoming games only
        prop_response = self.table.query(
            IndexName="ActivePredictionsIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("prediction_type").eq(
                "PROP"
            )
            & boto3.dynamodb.conditions.Key("commence_time").gte(current_time),
            Limit=limit // 2,
        )

        # Process game predictions
        for item in game_response.get("Items", []):
            predictions.append(
                {
                    "pk": item.get("pk"),
                    "sk": item.get("sk"),
                    "game_id": item.get("game_id", ""),
                    "sport": item.get("sport"),
                    "home_team": item.get("home_team"),
                    "away_team": item.get("away_team"),
                    "commence_time": item.get("commence_time"),
                    "model_version": item.get("model_version"),
                    "home_win_probability": float(item.get("home_win_probability", 0)),
                    "away_win_probability": float(item.get("away_win_probability", 0)),
                    "confidence_score": float(item.get("confidence_score", 0)),
                    "value_bets": item.get("value_bets", []),
                    "predicted_at": item.get("predicted_at"),
                    "status": item.get("status", "pending"),
                }
            )

        # Process prop predictions
        for item in prop_response.get("Items", []):
            predictions.append(
                {
                    "pk": item.get("pk"),
                    "sk": item.get("sk"),
                    "event_id": item.get("event_id", ""),
                    "player_name": item.get("player_name"),
                    "prop_type": item.get("prop_type"),
                    "commence_time": item.get("commence_time"),
                    "predicted_value": float(item.get("predicted_value", 0)),
                    "over_probability": float(item.get("over_probability", 0)),
                    "under_probability": float(item.get("under_probability", 0)),
                    "confidence_score": float(item.get("confidence_score", 0)),
                    "value_bets": item.get("value_bets", []),
                    "model_version": item.get("model_version"),
                    "predicted_at": item.get("predicted_at"),
                    "status": item.get("status", "pending"),
                }
            )

        return predictions[:limit]

    def get_game_predictions(self, limit: int = 25) -> List[Dict]:
        """Get only game predictions"""
        from datetime import datetime

        current_time = datetime.utcnow().isoformat()

        response = self.table.query(
            IndexName="ActivePredictionsIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("prediction_type").eq(
                "GAME"
            )
            & boto3.dynamodb.conditions.Key("commence_time").gte(current_time),
            Limit=limit,
        )

        predictions = []
        for item in response.get("Items", []):
            predictions.append(
                {
                    "pk": item.get("pk"),
                    "sk": item.get("sk"),
                    "game_id": item.get("game_id", ""),
                    "sport": item.get("sport"),
                    "home_team": item.get("home_team"),
                    "away_team": item.get("away_team"),
                    "commence_time": item.get("commence_time"),
                    "model_version": item.get("model_version"),
                    "home_win_probability": float(item.get("home_win_probability", 0)),
                    "away_win_probability": float(item.get("away_win_probability", 0)),
                    "confidence_score": float(item.get("confidence_score", 0)),
                    "value_bets": item.get("value_bets", []),
                    "predicted_at": item.get("predicted_at"),
                    "status": item.get("status", "pending"),
                }
            )

        return predictions

    def get_prop_predictions(self, limit: int = 25) -> List[Dict]:
        """Get prop predictions with proper pagination handling"""
        from datetime import datetime

        current_time = datetime.utcnow().isoformat()

        predictions = []
        last_evaluated_key = None

        while len(predictions) < limit:
            query_params = {
                "IndexName": "ActivePredictionsIndex",
                "KeyConditionExpression": boto3.dynamodb.conditions.Key(
                    "prediction_type"
                ).eq("PROP")
                & boto3.dynamodb.conditions.Key("commence_time").gte(current_time),
                "Limit": min(1000, limit - len(predictions)),  # Query in chunks
            }

            if last_evaluated_key:
                query_params["ExclusiveStartKey"] = last_evaluated_key

            response = self.table.query(**query_params)

            for item in response.get("Items", []):
                predictions.append(
                    {
                        "pk": item.get("pk"),
                        "sk": item.get("sk"),
                        "event_id": item.get("event_id", ""),
                        "player_name": item.get("player_name"),
                        "prop_type": item.get("prop_type"),
                        "commence_time": item.get("commence_time"),
                        "predicted_value": float(item.get("predicted_value", 0)),
                        "over_probability": float(item.get("over_probability", 0)),
                        "under_probability": float(item.get("under_probability", 0)),
                        "confidence_score": float(item.get("confidence_score", 0)),
                        "value_bets": item.get("value_bets", []),
                        "model_version": item.get("model_version"),
                        "predicted_at": item.get("predicted_at"),
                        "status": item.get("status", "pending"),
                    }
                )

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:  # No more results
                break

        return predictions[:limit]  # Ensure we don't exceed the requested limit
