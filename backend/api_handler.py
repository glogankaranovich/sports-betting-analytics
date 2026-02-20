import json

from api.utils import create_response
from api.user import (
    handle_get_profile,
    handle_get_subscription,
    handle_update_profile,
    handle_upgrade_subscription,
)


def lambda_handler(event, context):
    """
    Legacy Lambda handler for user profile/subscription endpoints only.
    
    All other endpoints have been migrated to modular handlers:
    - /health, /benny/dashboard, /compliance/log -> api.misc.lambda_handler
    - /games, /sports, /bookmakers, /player-props -> api.games.lambda_handler
    - /analyses, /top-analysis -> api.analyses.lambda_handler
    - /analytics, /model-* -> api.analytics.lambda_handler
    - /user-models, /custom-data -> api.user_data.lambda_handler
    """
    try:
        http_method = event.get("httpMethod", "")
        path = event.get("path", "")
        query_params = event.get("queryStringParameters") or {}

        # Handle CORS preflight
        if http_method == "OPTIONS":
            return create_response(200, {"message": "CORS preflight"})

        # User profile/subscription routes only
        if path == "/profile" and http_method == "GET":
            return handle_get_profile(query_params)
        elif path == "/profile" and http_method == "PUT":
            body = json.loads(event.get("body", "{}"))
            return handle_update_profile(body)
        elif path == "/subscription":
            return handle_get_subscription(query_params)
        elif path == "/subscription/upgrade" and http_method == "POST":
            body = json.loads(event.get("body", "{}"))
            return handle_upgrade_subscription(body)
        else:
            return create_response(404, {"error": "Endpoint not found"})

    except Exception as e:
        return create_response(500, {"error": f"Internal server error: {str(e)}"})
