"""Test script to check ESPN season-level team stats"""

import requests
import json

# ESPN team stats endpoints (season-level, not game-level)
test_endpoints = {
    "basketball_nba": "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/teams",
    "icehockey_nhl": "https://site.web.api.espn.com/apis/site/v2/sports/hockey/nhl/teams",
    "americanfootball_nfl": "https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/teams",
    "baseball_mlb": "https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb/teams",
    "soccer_epl": "https://site.web.api.espn.com/apis/site/v2/sports/soccer/eng.1/teams",
    "basketball_ncaab": "https://site.web.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/teams",
}

for sport_key, url in test_endpoints.items():
    print(f"\n{'='*60}")
    print(f"Testing {sport_key}")
    print(f"{'='*60}")
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        teams = data.get("sports", [{}])[0].get("leagues", [{}])[0].get("teams", [])
        
        if teams:
            print(f"✓ Found {len(teams)} teams")
            
            # Check first team for stats
            team = teams[0].get("team", {})
            team_name = team.get("displayName", "Unknown")
            team_id = team.get("id", "")
            
            print(f"  Sample team: {team_name} (ID: {team_id})")
            
            # Try to get team stats
            if team_id:
                stats_url = f"{url}/{team_id}/statistics"
                try:
                    stats_response = requests.get(stats_url, timeout=10)
                    stats_response.raise_for_status()
                    stats_data = stats_response.json()
                    
                    # Check for season stats
                    if "statistics" in stats_data or "splits" in stats_data:
                        print(f"  ✓ Season stats available")
                        print(f"    Keys: {list(stats_data.keys())[:5]}")
                    else:
                        print(f"  ✗ No season stats found")
                        print(f"    Response keys: {list(stats_data.keys())}")
                except Exception as e:
                    print(f"  ✗ Error fetching stats: {e}")
        else:
            print(f"✗ No teams found")
            
    except Exception as e:
        print(f"✗ Error: {e}")

print(f"\n{'='*60}")
print("Check if ESPN provides season-level team statistics")
print("='*60}")
