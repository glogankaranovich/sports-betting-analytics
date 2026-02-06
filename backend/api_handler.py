import json
import os
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

import boto3

from user_models import ModelPrediction, UserModel

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
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
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
        elif path == "/analyses":
            return handle_get_analyses(query_params)
        elif path == "/top-analysis":
            return handle_get_top_analysis(query_params)
        elif path == "/player-props":
            return handle_get_player_props(query_params)
        elif path == "/sports":
            return handle_get_sports()
        elif path == "/compliance/log" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))
            return handle_compliance_log(body)
        elif path == "/bookmakers":
            return handle_get_bookmakers()
        elif path == "/analytics":
            return handle_get_analytics(query_params)
        elif path == "/model-performance":
            return handle_get_model_performance(query_params)
        elif path == "/user-models" and http_method == "GET":
            return handle_list_user_models(query_params)
        elif path == "/user-models/predictions" and http_method == "GET":
            return handle_get_user_model_predictions(query_params)
        elif path == "/user-models" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))
            return handle_create_user_model(body)
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
    bookmaker = query_params.get("bookmaker")
    fetch_all = query_params.get("fetch_all", "false").lower() == "true"

    if fetch_all:
        limit = 10000
    else:
        limit = int(query_params.get("limit", "20"))

    last_evaluated_key = query_params.get("lastEvaluatedKey")

    if not sport:
        return create_response(400, {"error": "sport parameter is required"})

    # Frontend display bookmakers (backend collects from all bookmakers)
    display_bookmakers = {"fanatics", "fanduel", "draftkings", "betmgm"}

    try:
        # Parse pagination token if provided (only for paginated requests)
        exclusive_start_key = None
        if last_evaluated_key and not fetch_all:
            try:
                exclusive_start_key = json.loads(last_evaluated_key)
            except Exception:
                pass

        three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat()

        # Build filter expression
        filter_expr = boto3.dynamodb.conditions.Attr("latest").eq(True)
        if bookmaker:
            filter_expr = filter_expr & boto3.dynamodb.conditions.Attr(
                "sk"
            ).begins_with(f"{bookmaker}#")

        three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat()

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

        response = table.query(**query_kwargs)
        odds_items = response.get("Items", [])

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

            # Parse bookmaker and market from sk (format: bookmaker#market#LATEST)
            if "#" in item["sk"]:
                parts = item["sk"].split("#")
                bookmaker_name = parts[0]
                market = parts[1]

                # Filter by specific bookmaker if provided, otherwise use all display bookmakers
                allowed_bookmakers = {bookmaker} if bookmaker else display_bookmakers
                if bookmaker_name in allowed_bookmakers:
                    if bookmaker_name not in games_dict[game_id]["odds"]:
                        games_dict[game_id]["odds"][bookmaker_name] = {}

                    games_dict[game_id]["odds"][bookmaker_name][market] = item[
                        "outcomes"
                    ]

        games = list(games_dict.values())
        if not fetch_all:
            games = games[:limit]
        games = decimal_to_float(games)

        result = {"games": games, "count": len(games), "sport_filter": sport}

        if not fetch_all and "LastEvaluatedKey" in response:
            result["lastEvaluatedKey"] = json.dumps(response["LastEvaluatedKey"])

        return create_response(200, result)
    except Exception as e:
        return create_response(500, {"error": f"Error fetching games: {str(e)}"})


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


def handle_get_player_props(query_params: Dict[str, str]):
    """Get player props with optional filtering using GSI"""
    sport = query_params.get("sport")
    bookmaker = query_params.get("bookmaker")
    prop_type = query_params.get("prop_type")
    fetch_all = query_params.get("fetch_all", "false").lower() == "true"

    if fetch_all:
        limit = 10000
    else:
        limit = int(query_params.get("limit", "20"))

    last_evaluated_key = query_params.get("lastEvaluatedKey")

    if not sport:
        return create_response(400, {"error": "sport parameter is required"})

    # Frontend display bookmakers
    display_bookmakers = ["fanatics", "fanduel", "draftkings", "betmgm"]

    try:
        exclusive_start_key = None
        if last_evaluated_key and not fetch_all:
            try:
                exclusive_start_key = json.loads(last_evaluated_key)
            except Exception:
                pass

        three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat()

        # Build filter expression
        filter_expressions = [boto3.dynamodb.conditions.Attr("latest").eq(True)]

        if bookmaker:
            filter_expressions.append(
                boto3.dynamodb.conditions.Attr("bookmaker").eq(bookmaker)
            )
        else:
            bookmaker_filter = boto3.dynamodb.conditions.Attr("bookmaker").eq(
                display_bookmakers[0]
            )
            for bm in display_bookmakers[1:]:
                bookmaker_filter = bookmaker_filter | boto3.dynamodb.conditions.Attr(
                    "bookmaker"
                ).eq(bm)
            filter_expressions.append(bookmaker_filter)

        if prop_type:
            filter_expressions.append(
                boto3.dynamodb.conditions.Attr("market_key").eq(prop_type)
            )

        filter_expression = filter_expressions[0]
        for expr in filter_expressions[1:]:
            filter_expression = filter_expression & expr

        # Loop to get enough items (FilterExpression filters AFTER limit)
        props = []
        current_key = exclusive_start_key
        max_iterations = 10  # Safety limit to prevent infinite loops

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

            response = table.query(**query_kwargs)
            batch = response.get("Items", [])
            props.extend(batch)

            current_key = response.get("LastEvaluatedKey")

            if not current_key or (not fetch_all and len(props) >= limit):
                break

        if not fetch_all:
            props = props[:limit]
        pagination_key = (
            current_key if (not fetch_all and len(props) >= limit) else None
        )

        props = decimal_to_float(props)

        result = {
            "props": props,
            "count": len(props),
            "filters": {
                "sport": sport,
                "bookmaker": bookmaker,
                "prop_type": prop_type,
            },
        }

        if pagination_key and not fetch_all:
            result["lastEvaluatedKey"] = json.dumps(pagination_key)

        return create_response(200, result)
    except Exception as e:
        return create_response(500, {"error": f"Error fetching player props: {str(e)}"})


def handle_compliance_log(event_body: Dict[str, Any]):
    """Handle compliance logging requests"""
    try:
        from compliance_logger import ComplianceLogger

        compliance_logger = ComplianceLogger()
        session_id = event_body.get("sessionId")
        action = event_body.get("action")
        data = event_body.get("data", {})

        if not session_id or not action:
            return create_response(400, {"error": "Missing required fields"})

        success = compliance_logger.log_user_action(session_id, action, data)

        if success:
            return create_response(200, {"success": True})
        else:
            return create_response(500, {"error": "Failed to log action"})

    except Exception as e:
        print(f"Error logging compliance action: {str(e)}")
        return create_response(500, {"error": str(e)})


def handle_get_analyses(query_params: Dict[str, str]):
    """Get ML analyses using GSI1 sorted by confidence"""
    try:
        sport = query_params.get("sport", "basketball_nba")
        model = query_params.get("model")
        bookmaker = query_params.get("bookmaker")
        analysis_type = query_params.get("type", "game")  # "game" or "prop"
        fetch_all = query_params.get("fetch_all", "false").lower() == "true"

        # If fetch_all, don't use limit from query params
        if fetch_all:
            limit = 10000  # High limit to get everything
        else:
            limit = int(query_params.get("limit", "20"))

        last_evaluated_key_str = query_params.get("lastEvaluatedKey")

        # Parse lastEvaluatedKey if provided (only for paginated requests)
        last_evaluated_key = None
        if last_evaluated_key_str and not fetch_all:
            try:
                last_evaluated_key = json.loads(last_evaluated_key_str)
            except Exception:
                pass

        # Build analysis_pk: ANALYSIS#{sport}#{bookmaker}#{model}#{type}
        if not bookmaker or not model:
            return create_response(
                400, {"error": "Both bookmaker and model are required"}
            )

        analysis_pk = f"ANALYSIS#{sport}#{bookmaker}#{model}#{analysis_type}"

        # Time filtering - show analyses from 3 hours ago onwards
        three_hours_ago = (datetime.utcnow() - timedelta(hours=3)).isoformat()

        # Query using AnalysisTimeGSI
        query_kwargs = {
            "IndexName": "AnalysisTimeGSI",
            "KeyConditionExpression": boto3.dynamodb.conditions.Key(
                "analysis_time_pk"
            ).eq(analysis_pk)
            & boto3.dynamodb.conditions.Key("commence_time").gte(three_hours_ago),
            "ScanIndexForward": False,  # Most recent first
            "Limit": limit,
        }

        if last_evaluated_key and not fetch_all:
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = table.query(**query_kwargs)
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
            }

            # Add player_name for prop analyses
            if item.get("player_name"):
                analysis["player_name"] = item.get("player_name")

            # Add market_key for prop analyses
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

        # Add pagination token only if not fetching all and there are more results
        if not fetch_all and response.get("LastEvaluatedKey"):
            result["lastEvaluatedKey"] = json.dumps(response["LastEvaluatedKey"])

        return create_response(200, result)

    except Exception as e:
        return create_response(500, {"error": f"Error fetching analyses: {str(e)}"})


def handle_get_top_analysis(query_params: Dict[str, str]):
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
                response = table.query(
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
            return create_response(
                200, {"top_analysis": None, "sport": sport, "bookmaker": bookmaker}
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

        return create_response(
            200,
            {
                "top_analysis": decimal_to_float(top_analysis),
                "sport": sport,
                "bookmaker": bookmaker,
            },
        )

    except Exception as e:
        return create_response(500, {"error": f"Error fetching top analysis: {str(e)}"})


def handle_get_analytics(query_params: Dict[str, str]):
    """Get model analytics data from DynamoDB cache"""
    try:
        print(f"Analytics request - query_params: {query_params}")
        metric_type = query_params.get("type", "summary")
        print(f"Metric type: {metric_type}")

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
            return create_response(
                404, {"error": f"No cached data found for {metric_type}"}
            )

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


# User Models API Handlers
def handle_list_user_models(query_params: Dict[str, str]):
    """List all models for a user"""
    try:
        from user_models import UserModel

        user_id = query_params.get("user_id")
        if not user_id:
            return create_response(400, {"error": "user_id parameter required"})

        models = UserModel.list_by_user(user_id)
        return create_response(200, {"models": [decimal_to_float(m) for m in models]})
    except Exception as e:
        return create_response(500, {"error": f"Error listing models: {str(e)}"})


def handle_create_user_model(body: Dict[str, Any]):
    """Create a new user model"""
    try:
        from user_models import UserModel, validate_model_config

        # Validate required fields
        required = ["user_id", "name", "sport", "bet_types", "data_sources"]
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
            user_id=body["user_id"],
            name=body["name"],
            description=body.get("description", ""),
            sport=body["sport"],
            bet_types=body["bet_types"],
            data_sources=body["data_sources"],
            min_confidence=body.get("min_confidence", 0.6),
            status=body.get("status", "active"),
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
