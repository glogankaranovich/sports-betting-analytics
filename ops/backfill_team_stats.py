"""Backfill team stats from historical games for all sports"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from datetime import datetime
from team_stats_collector import TeamStatsCollector
import requests

# Historical date ranges for all sports (sample dates from last completed season)
HISTORICAL_RANGES = {
    "basketball_nba": {
        "sample_dates": ["20260215", "20260201", "20260115"],  # Current season
        "description": "NBA 2025-26 season"
    },
    "icehockey_nhl": {
        "sample_dates": ["20260215", "20260201", "20260115"],  # Current season
        "description": "NHL 2025-26 season"
    },
    "americanfootball_nfl": {
        "sample_dates": ["20260115", "20260101", "20251215"],  # Current season
        "description": "NFL 2025-26 season"
    },
    "baseball_mlb": {
        "sample_dates": ["20250915", "20250901", "20250815"],  # Last season
        "description": "MLB 2025 season"
    },
    "soccer_epl": {
        "sample_dates": ["20260215", "20260201", "20260115"],  # Current season
        "description": "EPL 2025-26 season"
    },
    "soccer_usa_mls": {
        "sample_dates": ["20251015", "20251001", "20250915"],  # Last season
        "description": "MLS 2025 season"
    },
    "basketball_ncaab": {
        "sample_dates": ["20260215", "20260201", "20260115"],  # Current season
        "description": "NCAA Men's Basketball 2025-26"
    },
    "basketball_wncaab": {
        "sample_dates": ["20260215", "20260201", "20260115"],  # Current season
        "description": "NCAA Women's Basketball 2025-26"
    },
    "americanfootball_ncaaf": {
        "sample_dates": ["20251115", "20251101", "20251015"],  # Last season
        "description": "NCAA Football 2025"
    },
    "basketball_wnba": {
        "sample_dates": ["20250815", "20250801", "20250715"],  # Last season
        "description": "WNBA 2025 season"
    },
}

SPORT_MAP = {
    "basketball_nba": "basketball/nba",
    "icehockey_nhl": "hockey/nhl",
    "americanfootball_nfl": "football/nfl",
    "baseball_mlb": "baseball/mlb",
    "soccer_epl": "soccer/eng.1",
    "soccer_usa_mls": "soccer/usa.1",
    "basketball_ncaab": "basketball/mens-college-basketball",
    "basketball_wncaab": "basketball/womens-college-basketball",
    "americanfootball_ncaaf": "football/college-football",
    "basketball_wnba": "basketball/wnba",
}


def backfill_sport(sport: str, sample_dates: list, description: str):
    """
    Backfill team stats by fetching historical games from ESPN.
    
    Args:
        sport: Sport key (e.g., 'baseball_mlb')
        sample_dates: List of dates to sample (YYYYMMDD format)
        description: Human-readable description
    """
    print(f"\n{'='*60}")
    print(f"Backfilling {sport}")
    print(f"{description}")
    print(f"{'='*60}\n")
    
    collector = TeamStatsCollector()
    espn_sport = SPORT_MAP.get(sport)
    
    if not espn_sport:
        print(f"✗ Sport {sport} not configured")
        return 0
    
    base_url = "https://site.web.api.espn.com/apis/site/v2/sports"
    total_games = 0
    
    for date_str in sample_dates:
        print(f"Fetching games from {date_str}...")
        
        try:
            scoreboard_url = f"{base_url}/{espn_sport}/scoreboard?dates={date_str}"
            response = requests.get(scoreboard_url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            events = data.get("events", [])
            print(f"  Found {len(events)} games")
            
            for event in events:
                game_id = event.get("id")
                if not game_id:
                    continue
                
                # Fetch and store team stats
                team_stats = collector._fetch_espn_team_stats(game_id, sport)
                
                if team_stats:
                    collector._store_team_stats(game_id, team_stats, sport)
                    total_games += 1
                    
                    # Show first team's stats as sample
                    if total_games == 1:
                        first_team = list(team_stats.keys())[0]
                        stat_count = len(team_stats[first_team])
                        print(f"    ✓ Sample: {first_team} ({stat_count} stats)")
                else:
                    print(f"    ✗ No stats for game {game_id}")
                    
        except Exception as e:
            print(f"  ✗ Error processing {date_str}: {e}")
            continue
    
    print(f"\n✓ Backfilled {total_games} games for {sport}")
    return total_games


def main():
    """Backfill stats for all sports"""
    print("="*60)
    print("Historical Team Stats Backfill")
    print("="*60)
    print("\nThis will fetch team stats from past season games")
    print("for all sports to populate the database.\n")
    
    # Allow filtering by sport
    if len(sys.argv) > 1:
        sports_to_process = [sys.argv[1]]
        if sports_to_process[0] not in HISTORICAL_RANGES:
            print(f"Unknown sport: {sports_to_process[0]}")
            print(f"Available: {', '.join(HISTORICAL_RANGES.keys())}")
            return
    else:
        sports_to_process = HISTORICAL_RANGES.keys()
    
    results = {}
    for sport in sports_to_process:
        config = HISTORICAL_RANGES[sport]
        games = backfill_sport(sport, config["sample_dates"], config["description"])
        results[sport] = games
    
    print("\n" + "="*60)
    print("Backfill Summary")
    print("="*60)
    for sport, count in results.items():
        status = "✓" if count > 0 else "✗"
        print(f"{status} {sport:30s} {count:3d} games")
    print(f"\nTotal: {sum(results.values())} games processed")
    print("="*60)


if __name__ == "__main__":
    main()
