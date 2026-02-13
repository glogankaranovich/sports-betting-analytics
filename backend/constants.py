"""
Constants for sports betting analytics platform.
Read from environment variables set by infrastructure.
"""
import os

# Parse from environment variables (comma-separated strings or JSON)
SUPPORTED_SPORTS = os.environ.get(
    "SUPPORTED_SPORTS",
    "basketball_nba,americanfootball_nfl,baseball_mlb,icehockey_nhl,soccer_epl",
).split(",")

SYSTEM_MODELS = os.environ.get(
    "SYSTEM_MODELS",
    "consensus,value,momentum,contrarian,hot_cold,rest_schedule,matchup,injury_aware,ensemble,benny",
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
    "benny": "Benny Model",
}

BET_TYPES = ["game", "prop"]
MARKET_TYPES = ["h2h", "spreads", "totals"]
