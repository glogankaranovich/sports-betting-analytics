#!/usr/bin/env python3
"""
Generate team ID mappings for all leagues from ESPN API
"""

import requests
import json

def get_teams(sport, league):
    """Fetch all teams for a sport/league"""
    url = f"http://sports.core.api.espn.com/v2/sports/{sport}/leagues/{league}/teams"
    response = requests.get(url, params={"limit": 100})
    data = response.json()
    
    teams = {}
    for item in data.get("items", []):
        team_url = item.get("$ref")
        if team_url:
            team_data = requests.get(team_url).json()
            team_id = team_data.get("id")
            team_name = team_data.get("displayName")
            if team_id and team_name:
                teams[team_name] = str(team_id)
    
    return teams

# Fetch all leagues
print("Fetching team mappings from ESPN API...")
print()

mappings = {
    "basketball_nba": get_teams("basketball", "nba"),
    "americanfootball_nfl": get_teams("football", "nfl"),
    "baseball_mlb": get_teams("baseball", "mlb"),
    "icehockey_nhl": get_teams("hockey", "nhl"),
}

# Generate Python code
print('        team_mapping = {')
for sport, teams in mappings.items():
    print(f'            "{sport}": {{')
    for team_name in sorted(teams.keys()):
        team_id = teams[team_name]
        print(f'                "{team_name}": "{team_id}",')
    print('            },')
print('        }')
print()
print(f"Total teams: {sum(len(teams) for teams in mappings.values())}")
