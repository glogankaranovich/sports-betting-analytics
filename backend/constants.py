"""
Constants for sports betting analytics platform.
Read from environment variables set by infrastructure.
"""
import os

# Parse from environment variables (comma-separated strings or JSON)
SUPPORTED_SPORTS = os.environ.get(
    "SUPPORTED_SPORTS",
    "basketball_nba,americanfootball_nfl,baseball_mlb,icehockey_nhl,soccer_epl,basketball_mens-college-basketball,basketball_womens-college-basketball,football_college-football",
).split(",")

SYSTEM_MODELS = os.environ.get(
    "SYSTEM_MODELS",
    "consensus,value,momentum,contrarian,hot_cold,rest_schedule,matchup,injury_aware,news,ensemble,fundamentals,player_stats",
).split(",")

SUPPORTED_BOOKMAKERS = os.environ.get(
    "SUPPORTED_BOOKMAKERS", "draftkings,fanduel,betmgm,caesars"
).split(",")

TIME_RANGES = [
    int(x) for x in os.environ.get("TIME_RANGES", "30,90,180,365").split(",")
]

# Static mappings (can also be env vars if needed)
SPORT_NAMES = {
    "basketball_nba": "NBA",
    "americanfootball_nfl": "NFL",
    "baseball_mlb": "MLB",
    "icehockey_nhl": "NHL",
    "soccer_epl": "EPL",
    "basketball_mens-college-basketball": "NCAA Men's Basketball",
    "basketball_womens-college-basketball": "NCAA Women's Basketball",
    "football_college-football": "NCAA Football",
}

MODEL_NAMES = {
    "consensus": "Consensus Model",
    "value": "Value Model",
    "momentum": "Momentum Model",
    "contrarian": "Contrarian Model",
    "hot_cold": "Hot/Cold Model",
    "rest_schedule": "Rest/Schedule Model",
    "matchup": "Matchup Model",
    "injury_aware": "Injury-Aware Model",
    "ensemble": "Ensemble Model",
    "fundamentals": "Fundamentals Model",
    "news": "News Sentiment Model",
    "benny": "Benny Model",
    "player_stats": "Player Stats Model",
}

BET_TYPES = ["game", "prop"]
MARKET_TYPES = ["h2h", "spreads", "totals"]
