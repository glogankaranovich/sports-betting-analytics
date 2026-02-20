"""
Lambda handler to calculate rolling PER averages for NBA players
"""
import json
import os
from per_calculator import PERCalculator

def handler(event, context):
    """Calculate rolling PER for players"""
    per_calc = PERCalculator()
    
    # Parse request
    body = json.loads(event.get("body", "{}")) if event.get("body") else {}
    player_name = body.get("player_name")
    games = body.get("games", 10)
    
    if not player_name:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "player_name required"})
        }
    
    # Calculate rolling PER
    per_data = per_calc.calculate_rolling_per(player_name, games)
    
    if not per_data:
        return {
            "statusCode": 404,
            "body": json.dumps({"error": "No stats found for player"})
        }
    
    # Store the result
    per_calc.store_player_per(player_name, per_data)
    
    return {
        "statusCode": 200,
        "body": json.dumps(per_data, default=str)
    }
