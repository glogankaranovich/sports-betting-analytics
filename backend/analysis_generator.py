import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from typing import Any, Dict

import boto3

from ml.dynamic_weighting import DynamicModelWeighting
from ml.models import AnalysisResult, ModelFactory

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
        import traceback
        traceback.print_exc()
        
        # Emit CloudWatch metric for monitoring
        try:
            import boto3
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.put_metric_data(
                Namespace='SportsAnalytics/AnalysisGenerator',
                MetricData=[{
                    'MetricName': 'AnalysisGenerationError',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Sport', 'Value': event.get('sport', 'unknown')},
                        {'Name': 'Model', 'Value': event.get('model', 'unknown')},
                        {'Name': 'BetType', 'Value': event.get('bet_type', 'unknown')}
                    ]
                }]
            )
        except:
            pass  # Don't fail on metric emission
        
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

        # Initialize dynamic weighting
        weighting = DynamicModelWeighting()

        # Process games in parallel
        def process_game(game_item):
            game_id, game_data = game_item
            game_count = 0
            game_info = game_data["items"][0]
            bookmakers = list(game_data["bookmakers"])

            analysis_result = model.analyze_game_odds(
                game_id, game_data["items"], game_info
            )

            if analysis_result:
                # Models now handle confidence adjustment internally via _adjust_confidence()
                for bookmaker in bookmakers:
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
                        recommended_odds=analysis_result.recommended_odds,
                    )
                    
                    bookmaker_item = next((item for item in game_data["items"] if item.get("bookmaker") == bookmaker and item.get("market_key") == "h2h"), None)
                    
                    analysis_dict = bookmaker_result.to_dynamodb_item()
                    if bookmaker_item and "outcomes" in bookmaker_item:
                        analysis_dict["all_outcomes"] = bookmaker_item["outcomes"]
                    
                    store_analysis(analysis_dict)
                    game_count += 1
            
            return game_count

        # Use ThreadPoolExecutor for parallel processing
        error_count = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_game, game) for game in games_to_process]
            for future in as_completed(futures):
                try:
                    count += future.result()
                except Exception as e:
                    error_count += 1
                    print(f"Error processing game: {e}")
                    import traceback
                    traceback.print_exc()

        # Emit metric if we had errors
        if error_count > 0:
            try:
                import boto3
                cloudwatch = boto3.client('cloudwatch')
                cloudwatch.put_metric_data(
                    Namespace='SportsAnalytics/AnalysisGenerator',
                    MetricData=[{
                        'MetricName': 'GameProcessingErrors',
                        'Value': error_count,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Sport', 'Value': sport},
                            {'Name': 'Model', 'Value': model.__class__.__name__}
                        ]
                    }]
                )
            except:
                pass

        return count

    except Exception as e:
        # Critical error in setup/query - this should fail the Lambda
        print(f"Critical error generating game analysis: {e}")
        import traceback
        traceback.print_exc()
        raise


def generate_prop_analysis(sport: str, model, limit: int = None) -> int:
    """Generate prop analysis using the provided model with pagination"""
    try:
        from datetime import datetime, timedelta

        props = []
        last_evaluated_key = None
        total_items_processed = 0
        three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat()

        while True:
            query_kwargs = {
                "IndexName": "ActiveBetsIndexV2",
                "KeyConditionExpression": "active_bet_pk = :pk AND commence_time >= :time",
                "FilterExpression": "latest = :latest",
                "ExpressionAttributeValues": {
                    ":pk": f"PROP#{sport}",
                    ":time": three_hours_ago,
                    ":latest": True,
                },
            }

            if last_evaluated_key:
                query_kwargs["ExclusiveStartKey"] = last_evaluated_key

            response = table.query(**query_kwargs)

            batch_size = len(response["Items"])
            props.extend(response["Items"])
            total_items_processed += batch_size

            last_evaluated_key = response.get("LastEvaluatedKey")

            print(
                f"Processed batch of {batch_size} items, total: {total_items_processed}"
            )

            if not last_evaluated_key:
                break

        print(f"Total prop items processed: {total_items_processed}")

        # Group props by event_id, player, market, AND point (across all bookmakers)
        grouped_props = {}
        for item in props:
            key = (
                item.get("event_id"),
                item.get("player_name"),
                item.get("market_key"),
                item.get("point"),  # Include point in grouping key
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

        # Initialize dynamic weighting
        weighting = DynamicModelWeighting()

        # Process props in parallel
        def process_prop(grouped_prop):
            prop_count = 0
            bookmakers = list(grouped_prop["bookmakers"])
            grouped_prop["bookmakers"] = bookmakers

            analysis_result = model.analyze_prop_odds(grouped_prop)

            if analysis_result:
                # Models now handle confidence adjustment internally via _adjust_confidence()
                for bookmaker in bookmakers:
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
                        recommended_odds=analysis_result.recommended_odds,
                    )
                    
                    analysis_dict = bookmaker_result.to_dynamodb_item()
                    if "outcomes" in grouped_prop:
                        analysis_dict["all_outcomes"] = grouped_prop["outcomes"]
                    
                    store_analysis(analysis_dict)
                    prop_count += 1
            
            return prop_count

        # Use ThreadPoolExecutor for parallel processing
        error_count = 0
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(process_prop, prop) for prop in props_to_process]
            for future in as_completed(futures):
                try:
                    count += future.result()
                except Exception as e:
                    error_count += 1
                    print(f"Error processing prop: {e}")
                    import traceback
                    traceback.print_exc()

        # Emit metric if we had errors
        if error_count > 0:
            try:
                import boto3
                cloudwatch = boto3.client('cloudwatch')
                cloudwatch.put_metric_data(
                    Namespace='SportsAnalytics/AnalysisGenerator',
                    MetricData=[{
                        'MetricName': 'PropProcessingErrors',
                        'Value': error_count,
                        'Unit': 'Count',
                        'Dimensions': [
                            {'Name': 'Sport', 'Value': sport},
                            {'Name': 'Model', 'Value': model.__class__.__name__}
                        ]
                    }]
                )
            except:
                pass

        return count

    except Exception as e:
        # Critical error in setup/query - this should fail the Lambda
        print(f"Critical error generating prop analysis: {e}")
        import traceback
        traceback.print_exc()
        raise


def store_analysis(analysis_item: Dict[str, Any]):
    """Store analysis in DynamoDB with inverse prediction"""
    try:
        # Convert floats to Decimals for DynamoDB
        analysis_item = float_to_decimal(analysis_item)

        # Store original prediction
        table.put_item(Item=analysis_item)
        print(
            f"Stored: {analysis_item['pk']} {analysis_item['sk']} - {analysis_item['prediction']}"
        )

        # Store inverse prediction
        inverse_item = create_inverse_prediction(analysis_item)
        if inverse_item:
            table.put_item(Item=inverse_item)
            print(
                f"Stored inverse: {inverse_item['pk']} {inverse_item['sk']} - {inverse_item['prediction']}"
            )

    except Exception as e:
        print(f"Error storing analysis: {e}")


def create_inverse_prediction(analysis_item: Dict[str, Any]) -> Dict[str, Any]:
    """Create inverse prediction for a given analysis with correct odds"""
    try:
        prediction = analysis_item.get("prediction", "")
        analysis_type = analysis_item.get("analysis_type", "game")
        confidence = float(analysis_item.get("confidence", 0.5))

        # Calculate inverse confidence (flip around 0.5)
        inverse_confidence = 1.0 - confidence

        # Determine inverse prediction based on type
        if analysis_type == "game":
            # For game predictions, flip the team
            home_team = analysis_item.get("home_team", "")
            away_team = analysis_item.get("away_team", "")

            # Check which team was predicted
            if home_team and home_team.lower() in prediction.lower():
                inverse_prediction = away_team
                predicted_team = home_team
            elif away_team and away_team.lower() in prediction.lower():
                inverse_prediction = home_team
                predicted_team = away_team
            else:
                # Can't determine inverse for complex predictions
                return None

            # Get opposite team's odds from all_outcomes
            inverse_odds = None
            if "all_outcomes" in analysis_item:
                for outcome in analysis_item["all_outcomes"]:
                    if outcome.get("name") == inverse_prediction:
                        inverse_odds = int(outcome.get("price", 0))
                        break

        elif analysis_type == "prop":
            # For props, flip over/under
            if "over" in prediction.lower():
                inverse_prediction = prediction.replace("Over", "Under").replace("over", "under")
                original_outcome = "Over"
                inverse_outcome = "Under"
            elif "under" in prediction.lower():
                inverse_prediction = prediction.replace("Under", "Over").replace("under", "over")
                original_outcome = "Under"
                inverse_outcome = "Over"
            else:
                return None
            
            # Get opposite outcome's odds from all_outcomes
            inverse_odds = None
            if "all_outcomes" in analysis_item:
                for outcome in analysis_item["all_outcomes"]:
                    if outcome.get("name") == inverse_outcome:
                        inverse_odds = int(outcome.get("price", 0))
                        break
        else:
            return None

        # Create inverse item with INVERSE suffix in SK
        inverse_item = analysis_item.copy()
        inverse_item["sk"] = analysis_item["sk"].replace("#LATEST", "#INVERSE")
        inverse_item["prediction"] = inverse_prediction
        inverse_item["confidence"] = Decimal(str(inverse_confidence))
        inverse_item["is_inverse"] = True
        inverse_item["original_prediction"] = prediction
        inverse_item["reasoning"] = "Inverse prediction - betting against the model"
        
        # Update recommended_odds for inverse if we found them
        if inverse_odds is not None:
            inverse_item["recommended_odds"] = inverse_odds
        
        # Recalculate ROI and risk level with inverse confidence and odds
        if inverse_item.get("recommended_odds"):
            odds = inverse_item["recommended_odds"]
            roi_multiplier = 100 / abs(odds) if odds < 0 else odds / 100
            inverse_roi = (inverse_confidence * roi_multiplier - (1 - inverse_confidence)) * 100
            inverse_item["roi"] = Decimal(str(round(inverse_roi, 1)))
            
            # Recalculate risk level based on inverse confidence
            if inverse_confidence >= 0.65:
                inverse_item["risk_level"] = "conservative"
            elif inverse_confidence >= 0.55:
                inverse_item["risk_level"] = "moderate"
            else:
                inverse_item["risk_level"] = "aggressive"

        return inverse_item

    except Exception as e:
        print(f"Error creating inverse prediction: {e}")
        return None
