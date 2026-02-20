"""
Lambda handler for Elo rating queries
"""
import json
import os
from elo_calculator import EloCalculator

def handler(event, context):
    """Get Elo ratings for teams"""
    elo_calc = EloCalculator()
    
    # Parse request
    body = json.loads(event.get("body", "{}"))
    sport = body.get("sport")
    teams = body.get("teams", [])
    
    if not sport or not teams:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "sport and teams required"})
        }
    
    # Get ratings
    ratings = {}
    for team in teams:
        ratings[team] = elo_calc.get_team_rating(sport, team)
    
    return {
        "statusCode": 200,
        "body": json.dumps({"ratings": ratings})
    }
