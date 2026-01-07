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
        elif path == "/player-props":
            return handle_get_player_props(query_params)
        elif path == "/sports":
            return handle_get_sports()
        elif path == "/compliance/log" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))
            return handle_compliance_log(body)
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
    bookmaker = query_params.get("bookmaker")
    limit = int(query_params.get("limit", "500"))

    # Frontend display bookmakers (backend collects from all bookmakers)
    display_bookmakers = {"fanatics", "fanduel", "draftkings", "betmgm"}

    # Supported sports for querying
    SUPPORTED_SPORTS = ["basketball_nba", "americanfootball_nfl", "soccer_epl"]

    # Determine which sports to query
    sports_to_query = [sport] if sport else SUPPORTED_SPORTS

    try:
        all_odds_items = []

        # Query each sport partition separately with time filtering
        from datetime import datetime, timedelta

        day_ago_time = (datetime.utcnow() - timedelta(days=1)).isoformat()

        for query_sport in sports_to_query:
            # Build filter expression
            filter_expr = boto3.dynamodb.conditions.Attr("latest").eq(True)
            if bookmaker:
                filter_expr = filter_expr & boto3.dynamodb.conditions.Attr(
                    "sk"
                ).begins_with(f"{bookmaker}#")

            response = table.query(
                IndexName="ActiveBetsIndexV2",
                KeyConditionExpression=boto3.dynamodb.conditions.Key(
                    "active_bet_pk"
                ).eq(f"GAME#{query_sport}")
                & boto3.dynamodb.conditions.Key("commence_time").gte(day_ago_time),
                FilterExpression=filter_expr,
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

            # Parse bookmaker and market from sk (format: bookmaker#market#LATEST)
            if "#" in item["sk"]:
                parts = item["sk"].split("#")
                bookmaker = parts[0]
                market = parts[1]  # Extract just the market name, ignore #LATEST

                # Filter by specific bookmaker if provided, otherwise use all display bookmakers
                allowed_bookmakers = {bookmaker} if bookmaker else display_bookmakers
                if bookmaker in allowed_bookmakers:
                    if bookmaker not in games_dict[game_id]["odds"]:
                        games_dict[game_id]["odds"][bookmaker] = {}

                    games_dict[game_id]["odds"][bookmaker][market] = item["outcomes"]

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
                        boto3.dynamodb.conditions.Attr("sk").begins_with(
                            f"{bookmaker}#"
                        )
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


def handle_get_insights(query_params: Dict[str, str]):
    """Get stored bet insights - DISABLED: Module removed during cleanup"""
    return create_response(501, {"error": "Insights feature temporarily disabled"})


def handle_get_top_insight(query_params: Dict[str, str]):
    """Get the single top insight - DISABLED: Module removed during cleanup"""
    return create_response(501, {"error": "Insights feature temporarily disabled"})


def _get_recent_game_analysis(sport, limit):
    """Helper to get recent game analysis with odds data"""
    # TODO: Implement actual data fetching from DynamoDB
    # For now, return empty list until we integrate with real data
    return []


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
