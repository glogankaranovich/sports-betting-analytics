import json
import boto3
import os
from typing import Dict, Any
from decimal import Decimal
from ml.models import ModelFactory

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

            # Group by game_id and bookmaker
            for item in response["Items"]:
                game_id = item["pk"][5:]  # Remove GAME# prefix
                bookmaker = item.get("bookmaker")
                key = f"{game_id}#{bookmaker}"

                if key not in games:
                    games[key] = {
                        "game_id": game_id,
                        "bookmaker": bookmaker,
                        "items": [],
                    }
                games[key]["items"].append(item)
                total_items_processed += 1

            last_evaluated_key = response.get("LastEvaluatedKey")
            if not last_evaluated_key:
                break

            print(
                f"Processed {total_items_processed} items, found {len(games)} unique game-bookmaker combinations"
            )

        print(
            f"Total items processed: {total_items_processed}, unique combinations: {len(games)}"
        )

        count = 0
        games_to_process = list(games.items())[:limit] if limit else list(games.items())

        for key, game_data in games_to_process:
            game_info = game_data["items"][0]  # Get game info from first item
            game_info["selected_bookmaker"] = game_data[
                "bookmaker"
            ]  # Pass bookmaker to model

            analysis_result = model.analyze_game_odds(
                game_data["game_id"], game_data["items"], game_info
            )

            if analysis_result:
                # Add bookmaker to analysis result before converting to DynamoDB item
                analysis_result.bookmaker = game_data["bookmaker"]
                analysis_item = analysis_result.to_dynamodb_item()

                store_analysis(analysis_item)
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

        count = 0
        props_to_process = props[:limit] if limit else props

        for item in props_to_process:
            analysis_result = model.analyze_prop_odds(item)

            if analysis_result:
                store_analysis(analysis_result.to_dynamodb_item())
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
