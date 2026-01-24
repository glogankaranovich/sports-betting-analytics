import json
import boto3
import os
from decimal import Decimal
from typing import Dict, Any
from datetime import datetime, timedelta

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
        elif path == "/analyses":
            return handle_get_analyses(query_params)
        elif path == "/insights":
            return handle_get_insights(query_params)
        elif path == "/top-insight":
            return handle_get_top_insight(query_params)
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
    limit = int(query_params.get("limit", "20"))
    last_evaluated_key = query_params.get("lastEvaluatedKey")

    if not sport:
        return create_response(400, {"error": "sport parameter is required"})

    # Frontend display bookmakers (backend collects from all bookmakers)
    display_bookmakers = {"fanatics", "fanduel", "draftkings", "betmgm"}

    try:
        # Parse pagination token if provided
        exclusive_start_key = None
        if last_evaluated_key:
            try:
                exclusive_start_key = json.loads(last_evaluated_key)
            except Exception:
                pass

        day_ago_time = (datetime.utcnow() - timedelta(days=1)).isoformat()

        # Build filter expression
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
            & boto3.dynamodb.conditions.Key("commence_time").gte(day_ago_time),
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

        games = list(games_dict.values())[:limit]
        games = decimal_to_float(games)

        result = {"games": games, "count": len(games), "sport_filter": sport}

        if "LastEvaluatedKey" in response:
            result["lastEvaluatedKey"] = json.dumps(response["LastEvaluatedKey"])

        return create_response(200, result)
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


def handle_get_player_props(query_params: Dict[str, str]):
    """Get player props with optional filtering using GSI"""
    sport = query_params.get("sport")
    bookmaker = query_params.get("bookmaker")
    prop_type = query_params.get("prop_type")
    limit = int(query_params.get("limit", "20"))
    last_evaluated_key = query_params.get("lastEvaluatedKey")

    if not sport:
        return create_response(400, {"error": "sport parameter is required"})

    # Frontend display bookmakers
    display_bookmakers = ["fanatics", "fanduel", "draftkings", "betmgm"]

    try:
        exclusive_start_key = None
        if last_evaluated_key:
            try:
                exclusive_start_key = json.loads(last_evaluated_key)
            except Exception:
                pass

        day_ago_time = (datetime.utcnow() - timedelta(days=1)).isoformat()

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
                & boto3.dynamodb.conditions.Key("commence_time").gte(day_ago_time),
                "FilterExpression": filter_expression,
                "Limit": limit * 3,
            }

            if current_key:
                query_kwargs["ExclusiveStartKey"] = current_key

            response = table.query(**query_kwargs)
            batch = response.get("Items", [])
            props.extend(batch)

            current_key = response.get("LastEvaluatedKey")

            if not current_key or len(props) >= limit:
                break

        props = props[:limit]
        pagination_key = current_key if len(props) >= limit else None

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

        if pagination_key:
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
    """Get ML analyses using AnalysisGSI"""
    try:
        sport = query_params.get("sport", "basketball_nba")
        model = query_params.get("model")
        bookmaker = query_params.get("bookmaker")
        analysis_type = query_params.get("type", "game")  # "game" or "prop"
        limit = int(query_params.get("limit", "20"))
        last_evaluated_key_str = query_params.get("lastEvaluatedKey")

        # Parse lastEvaluatedKey if provided
        last_evaluated_key = None
        if last_evaluated_key_str:
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

        # Time filtering - only show analyses from last 24 hours
        day_ago_time = (datetime.utcnow() - timedelta(days=1)).isoformat()

        # Query using AnalysisTimeGSI for chronological ordering
        query_kwargs = {
            "IndexName": "AnalysisTimeGSI",
            "KeyConditionExpression": boto3.dynamodb.conditions.Key(
                "analysis_time_pk"
            ).eq(analysis_pk)
            & boto3.dynamodb.conditions.Key("commence_time").gte(day_ago_time),
            "ScanIndexForward": False,  # Most recent first
            "Limit": limit,
        }

        if last_evaluated_key:
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

            analyses.append(analysis)

        analyses = decimal_to_float(analyses)

        result = {
            "analyses": analyses,
            "count": len(analyses),
            "sport": sport,
            "model_filter": model,
            "bookmaker_filter": bookmaker,
        }

        # Add pagination token if there are more results
        if response.get("LastEvaluatedKey"):
            result["lastEvaluatedKey"] = json.dumps(response["LastEvaluatedKey"])

        return create_response(200, result)

    except Exception as e:
        return create_response(500, {"error": f"Error fetching analyses: {str(e)}"})


def handle_get_insights(query_params: Dict[str, str]):
    """Get top insights (analyses) sorted by confidence"""
    try:
        sport = query_params.get("sport", "basketball_nba")
        model = query_params.get("model", "consensus")
        bookmaker = query_params.get("bookmaker", "fanduel")
        analysis_type = query_params.get("type", "game")  # "game" or "prop"
        limit = int(query_params.get("limit", "10"))
        last_evaluated_key_str = query_params.get("lastEvaluatedKey")

        # Parse lastEvaluatedKey if provided
        last_evaluated_key = None
        if last_evaluated_key_str:
            try:
                last_evaluated_key = json.loads(last_evaluated_key_str)
            except Exception:
                pass

        # Build analysis_pk: ANALYSIS#{sport}#{bookmaker}#{model}#{type}
        analysis_pk = f"ANALYSIS#{sport}#{bookmaker}#{model}#{analysis_type}"

        # Time filtering - only show insights for future games
        current_time = datetime.utcnow().isoformat()

        # Query using AnalysisTimeGSI
        query_kwargs = {
            "IndexName": "AnalysisTimeGSI",
            "KeyConditionExpression": boto3.dynamodb.conditions.Key(
                "analysis_time_pk"
            ).eq(analysis_pk)
            & boto3.dynamodb.conditions.Key("commence_time").gte(current_time),
            "ScanIndexForward": False,  # Most recent first
            "Limit": limit * 2,  # Get more than needed to sort by confidence
        }

        if last_evaluated_key:
            query_kwargs["ExclusiveStartKey"] = last_evaluated_key

        response = table.query(**query_kwargs)
        items = response.get("Items", [])

        # Convert to insights format
        insights = []
        for item in items:
            insight = {
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
                insight["player_name"] = item.get("player_name")

            insights.append(insight)

        # Sort by confidence (highest first)
        insights.sort(key=lambda x: x["confidence"], reverse=True)

        # Limit results
        insights = insights[:limit]

        insights = decimal_to_float(insights)

        result = {
            "insights": insights,
            "count": len(insights),
            "sport": sport,
            "model": model,
            "bookmaker": bookmaker,
        }

        # Add pagination token if there are more results
        if response.get("LastEvaluatedKey"):
            result["lastEvaluatedKey"] = json.dumps(response["LastEvaluatedKey"])

        return create_response(200, result)

    except Exception as e:
        return create_response(500, {"error": f"Error fetching insights: {str(e)}"})


def handle_get_top_insight(query_params: Dict[str, str]):
    """Get single top insight sorted by confidence across all models"""
    try:
        sport = query_params.get("sport", "basketball_nba")
        bookmaker = query_params.get("bookmaker", "fanduel")
        analysis_type = query_params.get("type", "game")  # "game" or "prop"

        # Time filtering - only show insights for future games
        current_time = datetime.utcnow().isoformat()

        # Query all three models
        all_insights = []
        for model in ["consensus", "value", "momentum"]:
            analysis_pk = f"ANALYSIS#{sport}#{bookmaker}#{model}#{analysis_type}"

            response = table.query(
                IndexName="AnalysisTimeGSI",
                KeyConditionExpression=boto3.dynamodb.conditions.Key(
                    "analysis_time_pk"
                ).eq(analysis_pk)
                & boto3.dynamodb.conditions.Key("commence_time").gte(current_time),
                ScanIndexForward=False,
                Limit=50,
            )

            for item in response.get("Items", []):
                insight = {
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
                if item.get("player_name"):
                    insight["player_name"] = item.get("player_name")
                all_insights.append(insight)

        if not all_insights:
            return create_response(
                200,
                {
                    "top_insight": None,
                    "sport": sport,
                    "bookmaker": bookmaker,
                },
            )

        # Sort by confidence and get top one across all models
        all_insights.sort(key=lambda x: x["confidence"], reverse=True)
        top_insight = decimal_to_float(all_insights[0])

        return create_response(
            200,
            {
                "top_insight": top_insight,
                "sport": sport,
                "bookmaker": bookmaker,
            },
        )

    except Exception as e:
        return create_response(500, {"error": f"Error fetching top insight: {str(e)}"})


def handle_get_analytics(query_params: Dict[str, str]):
    """Get model analytics data"""
    try:
        from model_analytics import ModelAnalytics

        analytics = ModelAnalytics(table_name)
        metric_type = query_params.get("type", "summary")
        model = query_params.get("model")

        # Route to appropriate metric
        if metric_type == "summary":
            data = analytics.get_model_performance_summary()
        elif metric_type == "by_sport":
            data = analytics.get_model_performance_by_sport(model)
        elif metric_type == "by_bet_type":
            data = analytics.get_model_performance_by_bet_type(model)
        elif metric_type == "over_time":
            if not model:
                return create_response(
                    400, {"error": "model parameter required for over_time"}
                )
            days = int(query_params.get("days", 30))
            data = analytics.get_model_performance_over_time(model, days)
        elif metric_type == "comparison":
            data = analytics.get_model_comparison()
        elif metric_type == "confidence":
            if not model:
                return create_response(
                    400, {"error": "model parameter required for confidence"}
                )
            data = analytics.get_model_confidence_analysis(model)
        elif metric_type == "weights":
            from ml.dynamic_weighting import DynamicModelWeighting

            weighting = DynamicModelWeighting()
            sport = query_params.get("sport", "basketball_nba")
            bet_type = query_params.get("bet_type", "game")

            # Get weights and performance metrics for all models
            weights = weighting.get_model_weights(sport, bet_type)

            model_metrics = {}
            for model_name in ["consensus", "value", "momentum"]:
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
        else:
            return create_response(
                400, {"error": f"Unknown metric type: {metric_type}"}
            )

        return create_response(200, decimal_to_float(data))

    except Exception as e:
        print(f"Error in analytics endpoint: {str(e)}")
        return create_response(500, {"error": f"Error fetching analytics: {str(e)}"})
