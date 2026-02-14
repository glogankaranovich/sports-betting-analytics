"""
API utilities and common functions
"""

import json
from decimal import Decimal
from typing import Any, Dict


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
