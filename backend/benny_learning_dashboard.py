"""Learning dashboard API endpoint — V2 retired, returns stub data"""
import json


def handler(event, context):
    """V2 learning retired. V1 uses adaptive thresholds, V3 uses flat sizing."""
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps({
            "features": None,
            "calibration": None,
            "thresholds": None,
            "note": "V2 learning retired. V1 uses adaptive thresholds, V3 uses flat sizing."
        })
    }
