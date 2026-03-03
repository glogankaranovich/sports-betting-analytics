"""Test script to check ESPN stat availability for all sports"""

import requests
import json

# Sample recent game IDs for each sport (you'll need to find real ones)
test_games = {
    "basketball_nba": ("basketball/nba", "401704962"),  # Recent NBA game
    "icehockey_nhl": ("hockey/nhl", "401559544"),  # Recent NHL game
    "americanfootball_nfl": ("football/nfl", "401671760"),  # Recent NFL game
    "baseball_mlb": ("baseball/mlb", "401581234"),  # Recent MLB game (off-season)
    "soccer_epl": ("soccer/eng.1", "704614"),  # Recent EPL game
    "basketball_ncaab": ("basketball/mens-college-basketball", "401639506"),  # Recent NCAA game
    "basketball_wncaab": ("basketball/womens-college-basketball", "401639507"),  # Recent WNCAA game
    "americanfootball_ncaaf": ("football/college-football", "401628478"),  # Recent NCAAF game
    "soccer_usa_mls": ("soccer/usa.1", "704615"),  # Recent MLS game (off-season)
    "basketball_wnba": ("basketball/wnba", "401639508"),  # Recent WNBA game (off-season)
}

base_url = "https://site.web.api.espn.com/apis/site/v2/sports"

for sport_key, (espn_path, game_id) in test_games.items():
    print(f"\n{'='*60}")
    print(f"Testing {sport_key}")
    print(f"{'='*60}")
    
    url = f"{base_url}/{espn_path}/summary?event={game_id}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        boxscore = data.get("boxscore", {})
        teams = boxscore.get("teams", [])
        
        if teams:
            print(f"✓ Stats available for {sport_key}")
            print(f"  Teams: {len(teams)}")
            
            # Show first team's stats
            if teams:
                team = teams[0]
                team_name = team.get("team", {}).get("displayName", "Unknown")
                stats = team.get("statistics", [])
                
                print(f"  Sample team: {team_name}")
                print(f"  Stat fields ({len(stats)}):")
                for stat in stats[:10]:  # Show first 10
                    label = stat.get("label", "")
                    value = stat.get("displayValue", "")
                    print(f"    - {label}: {value}")
                if len(stats) > 10:
                    print(f"    ... and {len(stats) - 10} more")
        else:
            print(f"✗ No stats available for {sport_key}")
            
    except Exception as e:
        print(f"✗ Error fetching {sport_key}: {e}")

print(f"\n{'='*60}")
print("Summary: Check which sports have team stats available")
print("='*60}")
