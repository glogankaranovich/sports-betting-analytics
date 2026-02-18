"""
API utilities and common functions
"""

import json
import os
from decimal import Decimal
from typing import Any, Dict, Callable

import boto3

# DynamoDB setup
dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
table_name = os.getenv("DYNAMODB_TABLE")
table = dynamodb.Table(table_name) if table_name else None


def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create standardized API response"""
    # Convert body to JSON string if it's not already
    if isinstance(body, str):
        body_str = body
    else:
        body_str = json.dumps(decimal_to_float(body), default=str)

    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS",
        },
        "body": body_str,
    }


def decimal_to_float(obj: Any) -> Any:
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(item) for item in obj]
    return obj


def calculate_roi(odds: int, confidence: float) -> dict:
    """Calculate ROI and risk level from odds and confidence"""
    if not odds:
        return {"roi": None, "risk_level": "unknown"}

    # Calculate implied probability from odds
    if odds < 0:
        implied_prob = abs(odds) / (abs(odds) + 100)
        roi_multiplier = 100 / abs(odds)
    else:
        implied_prob = 100 / (odds + 100)
        roi_multiplier = odds / 100

    # Calculate expected ROI: (confidence * roi_multiplier) - (1 - confidence)
    expected_roi = (confidence * roi_multiplier) - (1 - confidence)

    # Determine risk level
    if confidence >= 0.65:
        risk_level = "conservative"
    elif confidence >= 0.55:
        risk_level = "moderate"
    else:
        risk_level = "aggressive"

    return {
        "roi": round(expected_roi * 100, 1),  # As percentage
        "risk_level": risk_level,
        "implied_probability": round(implied_prob * 100, 1),
    }


class BaseAPIHandler:
    """Base class for API handlers with common request/response handling"""

    def __init__(self):
        self.table = table

    def lambda_handler(self, event: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Main Lambda handler entry point"""
        try:
            print(f"Handler called with event: {event}")

            http_method = event.get("httpMethod", "")
            path = event.get("path", "")
            query_params = event.get("queryStringParameters") or {}
            path_params = event.get("pathParameters") or {}

            print(f"Processing request: {http_method} {path}")

            # Handle CORS preflight
            if http_method == "OPTIONS":
                return create_response(200, {"message": "CORS preflight"})

            # Parse body for POST/PUT requests
            body = {}
            if http_method in ["POST", "PUT", "PATCH"] and event.get("body"):
                try:
                    body = json.loads(event.get("body", "{}"))
                except json.JSONDecodeError:
                    return create_response(400, {"error": "Invalid JSON in request body"})

            # Route to appropriate handler method
            return self.route_request(http_method, path, query_params, path_params, body)

        except Exception as e:
            print(f"Unhandled error in lambda_handler: {str(e)}")
            return self.handle_error(e)

    def route_request(
        self,
        http_method: str,
        path: str,
        query_params: Dict[str, str],
        path_params: Dict[str, str],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Route request to appropriate handler method.
        Override this in subclasses to implement routing logic.
        """
        raise NotImplementedError("Subclasses must implement route_request")

    def handle_error(self, error: Exception) -> Dict[str, Any]:
        """Handle errors and return appropriate response"""
        error_message = str(error)
        print(f"Error: {error_message}")

        # You can add more sophisticated error handling here
        # (e.g., different status codes for different error types)
        return create_response(500, {"error": f"Internal server error: {error_message}"})

    def validate_required_params(
        self, params: Dict[str, Any], required: list
    ) -> Dict[str, Any]:
        """Validate that required parameters are present"""
        missing = [param for param in required if not params.get(param)]
        if missing:
            return create_response(
                400, {"error": f"Missing required parameters: {', '.join(missing)}"}
            )
        return None

    def success_response(self, data: Any, status_code: int = 200) -> Dict[str, Any]:
        """Create a success response"""
        return create_response(status_code, data)

    def error_response(
        self, message: str, status_code: int = 400
    ) -> Dict[str, Any]:
        """Create an error response"""
        return create_response(status_code, {"error": message})
