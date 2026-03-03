"""Test script to check ESPN historical game stats"""

import requests
from datetime import datetime, timedelta

# Try to get scoreboard from a date in the past season
test_dates = {
    "baseball_mlb": ("baseball/mlb", "20250915"),  # September 2025 (last season)
    "basketball_wnba": ("basketball/wnba", "20250815"),  # August 2025 (last season)
    "basketball_ncaab": ("basketball/mens-college-basketball", "20250215"),  # Feb 2025
    "basketball_wncaab": ("basketball/womens-college-basketball", "20250215"),  # Feb 2025
}

base_url = "https://site.web.api.espn.com/apis/site/v2/sports"

for sport_key, (espn_path, date_str) in test_dates.items():
    print(f"\n{'='*60}")
    print(f"Testing {sport_key} on {date_str}")
    print(f"{'='*60}")
    
    # Get scoreboard for that date
    scoreboard_url = f"{base_url}/{espn_path}/scoreboard?dates={date_str}"
    
    try:
        response = requests.get(scoreboard_url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        events = data.get("events", [])
        
        if events:
            print(f"✓ Found {len(events)} games on {date_str}")
            
            # Try to get stats for first game
            game = events[0]
            game_id = game.get("id")
            home_team = game.get("competitions", [{}])[0].get("competitors", [{}])[0].get("team", {}).get("displayName", "Unknown")
            away_team = game.get("competitions", [{}])[0].get("competitors", [{}])[1].get("team", {}).get("displayName", "Unknown")
            
            print(f"  Sample game: {away_team} @ {home_team} (ID: {game_id})")
            
            # Try to get game stats
            if game_id:
                stats_url = f"{base_url}/{espn_path}/summary?event={game_id}"
                try:
                    stats_response = requests.get(stats_url, timeout=10)
                    stats_response.raise_for_status()
                    stats_data = stats_response.json()
                    
                    boxscore = stats_data.get("boxscore", {})
                    teams = boxscore.get("teams", [])
                    
                    if teams:
                        print(f"  ✓ Stats available!")
                        team = teams[0]
                        team_name = team.get("team", {}).get("displayName", "Unknown")
                        stats = team.get("statistics", [])
                        print(f"    Team: {team_name}")
                        print(f"    Stat fields: {len(stats)}")
                        for stat in stats[:5]:
                            label = stat.get("label", "")
                            value = stat.get("displayValue", "")
                            print(f"      - {label}: {value}")
                    else:
                        print(f"  ✗ No stats in boxscore")
                        
                except Exception as e:
                    print(f"  ✗ Error fetching game stats: {e}")
        else:
            print(f"✗ No games found on {date_str}")
            
    except Exception as e:
        print(f"✗ Error: {e}")

print(f"\n{'='*60}")
print("Summary: Can we get historical game stats from past seasons?")
print("='*60}")
