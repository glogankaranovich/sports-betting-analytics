import json
import boto3
import os
from decimal import Decimal
from typing import Dict, Any

# DynamoDB setup
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table_name = os.getenv("DYNAMODB_TABLE")
table = dynamodb.Table(table_name)


def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    return obj


def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response with CORS headers"""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        },
        "body": json.dumps(body, default=str),
    }


def lambda_handler(event, context):
    """Main Lambda handler for API requests"""
    try:
        print(f"Lambda handler called with event: {event}")

        http_method = event.get("httpMethod", "")
        path = event.get("path", "")
        query_params = event.get("queryStringParameters") or {}

        print(f"Processing request: {http_method} {path}")

        # Handle CORS preflight
        if http_method == "OPTIONS":
            return create_response(200, {"message": "CORS preflight"})

        # Route requests
        if path == "/health":
            return handle_health()
        elif path == "/games":
            return handle_get_games(query_params)
        elif path.startswith("/games/"):
            game_id = path.split("/")[-1]
            return handle_get_game(game_id)
        elif path == "/predictions":
            return handle_get_predictions(query_params)
        elif path == "/stored-predictions":
            return handle_get_stored_predictions(query_params)
        elif path == "/game-predictions":
            print("Handling game-predictions request")
            return handle_get_game_predictions(query_params)
        elif path == "/prop-predictions":
            print("Handling prop-predictions request")
            return handle_get_prop_predictions(query_params)
        elif path == "/player-props":
            return handle_get_player_props(query_params)
        elif path == "/sports":
            return handle_get_sports()
        elif path == "/bookmakers":
            return handle_get_bookmakers()
        else:
            return create_response(404, {"error": "Endpoint not found"})

    except Exception as e:
        return create_response(500, {"error": f"Internal server error: {str(e)}"})


def handle_health():
    """Health check endpoint"""
    return create_response(
        200,
        {
            "status": "healthy",
            "table": table_name,
            "environment": os.getenv("ENVIRONMENT", "unknown"),
        },
    )


def handle_get_games(query_params: Dict[str, str]):
    """Get all games with latest odds using GSI query"""
    sport = query_params.get("sport")
    limit = int(query_params.get("limit", "500"))

    # Frontend display bookmakers (backend collects from all bookmakers)
    display_bookmakers = {"fanatics", "fanduel", "draftkings", "betmgm"}

    # Supported sports for querying
    SUPPORTED_SPORTS = ["basketball_nba", "americanfootball_nfl", "soccer_epl"]

    # Determine which sports to query
    sports_to_query = [sport] if sport else SUPPORTED_SPORTS

    try:
        all_odds_items = []

        # Query each sport partition separately
        for query_sport in sports_to_query:
            response = table.query(
                IndexName="ActiveBetsIndexV2",
                KeyConditionExpression=boto3.dynamodb.conditions.Key(
                    "active_bet_pk"
                ).eq(f"GAME#{query_sport}"),
                FilterExpression=boto3.dynamodb.conditions.Attr("latest").eq(True),
                Limit=limit * 10,
            )
            all_odds_items.extend(response.get("Items", []))

        odds_items = all_odds_items

        # Group odds by game_id
        games_dict = {}
        for item in odds_items:
            # Extract game_id from GAME# prefix
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

            # Parse bookmaker and market from sk (format: bookmaker#market)
            if "#" in item["sk"]:
                bookmaker, market = item["sk"].split("#", 1)

                # Only include display bookmakers in frontend response
                if bookmaker in display_bookmakers:
                    if bookmaker not in games_dict[game_id]["odds"]:
                        games_dict[game_id]["odds"][bookmaker] = {}

                    games_dict[game_id]["odds"][bookmaker][market] = {
                        "outcomes": item["outcomes"]
                    }

        games = list(games_dict.values())[:limit]
        games = decimal_to_float(games)

        return create_response(
            200, {"games": games, "count": len(games), "sport_filter": sport}
        )
    except Exception as e:
        return create_response(500, {"error": f"Error fetching games: {str(e)}"})


def handle_get_game(game_id: str):
    """Get all betting data for a specific game"""
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key("pk").eq(game_id)
        )

        game_data = response.get("Items", [])

        if not game_data:
            return create_response(404, {"error": "Game not found"})

        game_data = decimal_to_float(game_data)

        return create_response(
            200, {"game_id": game_id, "bookmakers": game_data, "count": len(game_data)}
        )
    except Exception as e:
        return create_response(500, {"error": f"Error fetching game: {str(e)}"})


def handle_get_sports():
    """Get list of available sports"""
    try:
        response = table.scan(ProjectionExpression="sport")

        sports = set()
        for item in response.get("Items", []):
            if "sport" in item:
                sports.add(item["sport"])

        return create_response(
            200, {"sports": sorted(list(sports)), "count": len(sports)}
        )
    except Exception as e:
        return create_response(500, {"error": f"Error fetching sports: {str(e)}"})


def handle_get_bookmakers():
    """Get list of available bookmakers"""
    try:
        response = table.scan(ProjectionExpression="bookmaker")

        bookmakers = set()
        for item in response.get("Items", []):
            if "bookmaker" in item:
                bookmakers.add(item["bookmaker"])

        return create_response(
            200, {"bookmakers": sorted(list(bookmakers)), "count": len(bookmakers)}
        )
    except Exception as e:
        return create_response(500, {"error": f"Error fetching bookmakers: {str(e)}"})


def handle_get_predictions(query_params: Dict[str, str]):
    """Get ML predictions for games"""
    sport = query_params.get("sport")

    try:
        # Get games data using new schema
        filter_expression = boto3.dynamodb.conditions.Attr("pk").begins_with("GAME#")
        if sport:
            filter_expression = filter_expression & boto3.dynamodb.conditions.Attr(
                "sport"
            ).eq(sport)

        response = table.scan(FilterExpression=filter_expression, Limit=1000)

        # Group by game_id and reconstruct game structure
        games_by_id = {}
        for item in response.get("Items", []):
            # Extract game_id from pk (GAME#game_id)
            game_id = item.get("pk", "").replace("GAME#", "")
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

            # Parse sk to get bookmaker and market (bookmaker#market)
            sk_parts = item.get("sk", "").split("#")
            if len(sk_parts) >= 2:
                bookmaker = sk_parts[0]
                market = sk_parts[1]

                if bookmaker not in games_by_id[game_id]["odds"]:
                    games_by_id[game_id]["odds"][bookmaker] = {}

                games_by_id[game_id]["odds"][bookmaker][market] = {
                    "outcomes": item.get("outcomes", [])
                }

        # Generate predictions
        from ml.models import OddsAnalyzer

        analyzer = OddsAnalyzer()
        predictions = []

        for game_data in games_by_id.values():
            try:
                prediction = analyzer.analyze_game(game_data)
                predictions.append(
                    {
                        "game_id": game_data["game_id"],
                        "sport": game_data["sport"],
                        "home_team": game_data["home_team"],
                        "away_team": game_data["away_team"],
                        "commence_time": game_data["commence_time"],
                        "home_win_probability": prediction.home_win_probability,
                        "away_win_probability": prediction.away_win_probability,
                        "confidence_score": prediction.confidence_score,
                        "value_bets": prediction.value_bets,
                    }
                )
            except Exception:
                # Skip games with prediction errors
                continue

        return create_response(
            200, {"predictions": predictions, "count": len(predictions)}
        )
    except Exception as e:
        return create_response(
            500, {"error": f"Error generating predictions: {str(e)}"}
        )


def handle_get_stored_predictions(query_params: Dict[str, str]):
    """Get stored predictions from database"""
    limit = int(query_params.get("limit", "50"))

    try:
        from prediction_tracker import PredictionTracker

        tracker = PredictionTracker(table_name)
        predictions = tracker.get_predictions(limit)

        return create_response(
            200, {"predictions": predictions, "count": len(predictions)}
        )
    except Exception as e:
        return create_response(
            500, {"error": f"Error fetching stored predictions: {str(e)}"}
        )


def handle_get_game_predictions(query_params: Dict[str, str]):
    """Get game predictions only"""
    limit = int(
        query_params.get("limit", "1000")
    )  # Default to high limit if not specified

    try:
        print(f"Getting game predictions with limit: {limit}")
        from prediction_tracker import PredictionTracker

        tracker = PredictionTracker(table_name)
        predictions = tracker.get_game_predictions(limit)
        print(f"Found {len(predictions)} game predictions")

        return create_response(
            200, {"predictions": predictions, "count": len(predictions)}
        )
    except Exception as e:
        print(f"Error in handle_get_game_predictions: {str(e)}")
        import traceback

        traceback.print_exc()
        return create_response(
            500, {"error": f"Error fetching game predictions: {str(e)}"}
        )


def handle_get_prop_predictions(query_params: Dict[str, str]):
    """Get prop predictions only"""
    limit = int(
        query_params.get("limit", "1000")
    )  # Default to high limit if not specified

    try:
        print(f"Getting prop predictions with limit: {limit}")
        from prediction_tracker import PredictionTracker

        tracker = PredictionTracker(table_name)
        predictions = tracker.get_prop_predictions(limit)
        print(f"Found {len(predictions)} prop predictions")

        return create_response(
            200, {"predictions": predictions, "count": len(predictions)}
        )
    except Exception as e:
        print(f"Error in handle_get_prop_predictions: {str(e)}")
        import traceback

        traceback.print_exc()
        return create_response(
            500, {"error": f"Error fetching prop predictions: {str(e)}"}
        )


def handle_get_player_props(query_params: Dict[str, str]):
    """Get player props with optional filtering using GSI"""
    sport = query_params.get("sport")
    bookmaker = query_params.get("bookmaker")
    prop_type = query_params.get("prop_type")  # Filter by market_key
    limit = int(query_params.get("limit", "500"))

    # Frontend display bookmakers (backend collects from all bookmakers)
    display_bookmakers = {"fanatics", "fanduel", "draftkings", "betmgm"}

    # Supported sports for querying
    SUPPORTED_SPORTS = ["basketball_nba", "americanfootball_nfl", "soccer_epl"]

    # Determine which sports to query
    sports_to_query = [sport] if sport else SUPPORTED_SPORTS

    try:
        # Use ActiveBetsIndex GSI to query for PROP bet types efficiently
        props = []

        for query_sport in sports_to_query:
            last_evaluated_key = None

            while len(props) < limit:
                remaining_limit = limit - len(props)
                query_kwargs = {
                    "IndexName": "ActiveBetsIndexV2",
                    "KeyConditionExpression": boto3.dynamodb.conditions.Key(
                        "active_bet_pk"
                    ).eq(f"PROP#{query_sport}"),
                    "Limit": remaining_limit,
                }

                # Add filters as FilterExpression if provided
                filter_expressions = [
                    boto3.dynamodb.conditions.Attr("latest").eq(True)
                ]  # Always filter for latest
                if bookmaker:
                    filter_expressions.append(
                        boto3.dynamodb.conditions.Attr("bookmaker").eq(bookmaker)
                    )
                if prop_type:
                    filter_expressions.append(
                        boto3.dynamodb.conditions.Attr("market_key").eq(prop_type)
                    )

            if filter_expressions:
                filter_expression = filter_expressions[0]
                for expr in filter_expressions[1:]:
                    filter_expression = filter_expression & expr
                query_kwargs["FilterExpression"] = filter_expression

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = table.query(**query_kwargs)
            batch_props = response.get("Items", [])

            # Filter to only display bookmakers for frontend
            filtered_props = [
                prop
                for prop in batch_props
                if prop.get("bookmaker") in display_bookmakers
            ]
            props.extend(filtered_props)

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key or len(batch_props) == 0:
                break

        props = decimal_to_float(props)

        return create_response(
            200,
            {
                "props": props,
                "count": len(props),
                "filters": {
                    "sport": sport,
                    "bookmaker": bookmaker,
                    "prop_type": prop_type,
                },
            },
        )
    except Exception as e:
        return create_response(500, {"error": f"Error fetching player props: {str(e)}"})
