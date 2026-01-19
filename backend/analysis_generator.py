import json
import boto3
import os
from typing import Dict, Any
from decimal import Decimal
from ml.models import ModelFactory, AnalysisResult

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


def float_to_decimal(obj):
    """Convert float objects to Decimal for DynamoDB storage"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: float_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [float_to_decimal(v) for v in obj]
    return obj


def lambda_handler(event, context):
    """Generate ML analysis using model factory"""
    try:
        sport = event.get("sport", "basketball_nba")
        model_name = event.get("model", "consensus")
        bet_type = event.get("bet_type", "games")
        limit = event.get("limit")

        print(
            f"Generating {bet_type} analysis for {sport} using {model_name} model (limit: {limit})"
        )

        # Create model instance
        model = ModelFactory.create_model(model_name)

        if bet_type == "games":
            count = generate_game_analysis(sport, model, limit)
        elif bet_type == "props":
            count = generate_prop_analysis(sport, model, limit)
        else:
            game_count = generate_game_analysis(sport, model, limit)
            prop_count = generate_prop_analysis(sport, model, limit)
            count = game_count + prop_count

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": f"Generated {count} analyses for {sport} using {model_name} model",
                    "sport": sport,
                    "model": model_name,
                    "bet_type": bet_type,
                    "analyses_count": count,
                }
            ),
        }

    except Exception as e:
        print(f"Error: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


def generate_game_analysis(sport: str, model, limit: int = None) -> int:
    """Generate game analysis using the provided model with pagination"""
    try:
        games = {}
        last_evaluated_key = None
        total_items_processed = 0

        while True:
            query_kwargs = {
                "IndexName": "ActiveBetsIndexV2",
                "KeyConditionExpression": "active_bet_pk = :pk",
                "FilterExpression": "attribute_exists(latest)",
                "ExpressionAttributeValues": {":pk": f"GAME#{sport}"},
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = table.query(**query_kwargs)

            # Group by game_id only (across all bookmakers)
            for item in response["Items"]:
                game_id = item["pk"][5:]  # Remove GAME# prefix
                bookmaker = item.get("bookmaker")

                if game_id not in games:
                    games[game_id] = {
                        "game_id": game_id,
                        "items": [],
                        "bookmakers": set(),
                    }
                games[game_id]["items"].append(item)
                games[game_id]["bookmakers"].add(bookmaker)
                total_items_processed += 1

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

            print(
                f"Processed {total_items_processed} items, found {len(games)} unique games"
            )

        print(
            f"Total items processed: {total_items_processed}, unique games: {len(games)}"
        )

        count = 0
        games_to_process = list(games.items())[:limit] if limit else list(games.items())

        for game_id, game_data in games_to_process:
            game_info = game_data["items"][0]  # Get game info from first item
            bookmakers = list(game_data["bookmakers"])

            # Generate analysis once using all bookmakers' odds
            analysis_result = model.analyze_game_odds(
                game_id, game_data["items"], game_info
            )

            if analysis_result:
                # Store one record per bookmaker with the same analysis
                for bookmaker in bookmakers:
                    # Create a new AnalysisResult with the specific bookmaker
                    bookmaker_result = AnalysisResult(
                        game_id=analysis_result.game_id,
                        bookmaker=bookmaker,
                        model=analysis_result.model,
                        analysis_type=analysis_result.analysis_type,
                        sport=analysis_result.sport,
                        home_team=analysis_result.home_team,
                        away_team=analysis_result.away_team,
                        commence_time=analysis_result.commence_time,
                        player_name=analysis_result.player_name,
                        prediction=analysis_result.prediction,
                        confidence=analysis_result.confidence,
                        reasoning=analysis_result.reasoning,
                    )
                    store_analysis(bookmaker_result.to_dynamodb_item())
                    count += 1

        return count

    except Exception as e:
        print(f"Error generating game analysis: {e}")
        return 0


def generate_prop_analysis(sport: str, model, limit: int = None) -> int:
    """Generate prop analysis using the provided model with pagination"""
    try:
        props = []
        last_evaluated_key = None
        total_items_processed = 0

        while True:
            query_kwargs = {
                "IndexName": "ActiveBetsIndexV2",
                "KeyConditionExpression": "active_bet_pk = :pk",
                "FilterExpression": "attribute_exists(latest)",
                "ExpressionAttributeValues": {":pk": f"PROP#{sport}"},
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = table.query(**query_kwargs)

            props.extend(response["Items"])
            total_items_processed += len(response["Items"])

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

            print(f"Processed {total_items_processed} prop items")

        print(f"Total prop items processed: {total_items_processed}")

        # Group props by event_id, player, and market (across all bookmakers)
        grouped_props = {}
        for item in props:
            key = (
                item.get("event_id"),
                item.get("player_name"),
                item.get("market_key"),
            )
            if key not in grouped_props:
                grouped_props[key] = {
                    "event_id": item.get("event_id"),
                    "player_name": item.get("player_name"),
                    "market_key": item.get("market_key"),
                    "sport": item.get("sport"),
                    "commence_time": item.get("commence_time"),
                    "point": item.get("point"),
                    "outcomes": [],
                    "bookmakers": set(),
                }
            grouped_props[key]["outcomes"].append(
                {"name": item.get("outcome"), "price": int(item.get("price", 0))}
            )
            grouped_props[key]["bookmakers"].add(item.get("bookmaker"))

        count = 0
        grouped_list = list(grouped_props.values())
        props_to_process = grouped_list[:limit] if limit else grouped_list

        for grouped_prop in props_to_process:
            # Convert bookmakers set to list for JSON serialization
            bookmakers = list(grouped_prop["bookmakers"])
            grouped_prop["bookmakers"] = bookmakers

            # Generate analysis once using all bookmakers
            analysis_result = model.analyze_prop_odds(grouped_prop)

            if analysis_result:
                # Store one record per bookmaker with the same analysis
                for bookmaker in bookmakers:
                    # Create a new AnalysisResult with the specific bookmaker
                    bookmaker_result = AnalysisResult(
                        game_id=analysis_result.game_id,
                        bookmaker=bookmaker,
                        model=analysis_result.model,
                        analysis_type=analysis_result.analysis_type,
                        sport=analysis_result.sport,
                        home_team=analysis_result.home_team,
                        away_team=analysis_result.away_team,
                        commence_time=analysis_result.commence_time,
                        player_name=analysis_result.player_name,
                        market_key=analysis_result.market_key,
                        prediction=analysis_result.prediction,
                        confidence=analysis_result.confidence,
                        reasoning=analysis_result.reasoning,
                    )
                    store_analysis(bookmaker_result.to_dynamodb_item())
                    count += 1

        return count

    except Exception as e:
        print(f"Error generating prop analysis: {e}")
        return 0


def store_analysis(analysis_item: Dict[str, Any]):
    """Store analysis in DynamoDB"""
    try:
        # Convert floats to Decimals for DynamoDB
        analysis_item = float_to_decimal(analysis_item)
        table.put_item(Item=analysis_item)
        print(
            f"Stored: {analysis_item['pk']} {analysis_item['sk']} - {analysis_item['prediction']}"
        )
    except Exception as e:
        print(f"Error storing analysis: {e}")
