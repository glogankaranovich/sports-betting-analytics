"""Learning dashboard API endpoint"""
import json
import os
from typing import Dict, Any
import boto3
from boto3.dynamodb.conditions import Key


dynamodb = boto3.resource("dynamodb", region_name="us-east-1")


def handler(event, context):
    """Get learning metrics for Benny v2"""
    table_name = os.environ.get("DYNAMODB_TABLE", "carpool-bets-v2-dev")
    table = dynamodb.Table(table_name)
    
    pk = "BENNY_V2#LEARNING"
    
    # Get all learning data
    response = table.query(
        KeyConditionExpression=Key("pk").eq(pk)
    )
    
    items = response.get("Items", [])
    
    # Organize by type
    data = {
        "features": None,
        "calibration": None,
        "thresholds": None
    }
    
    for item in items:
        sk = item.get("sk")
        if sk == "FEATURES":
            data["features"] = item.get("insights", {})
        elif sk == "CALIBRATION":
            data["calibration"] = item.get("calibration", {})
        elif sk == "THRESHOLDS":
            data["thresholds"] = item.get("thresholds", {})
    
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*"
        },
        "body": json.dumps(data, default=str)
    }
