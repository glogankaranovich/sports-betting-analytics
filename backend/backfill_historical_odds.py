"""
Backfill historical odds and outcomes from The Odds API

This script fetches historical odds data for the past 2 years and stores it in DynamoDB.
Run once per environment (dev, beta, prod) to populate historical data for backtesting.

Usage:
    python backfill_historical_odds.py --env dev --api-key YOUR_API_KEY
    python backfill_historical_odds.py --env beta --api-key YOUR_API_KEY
    python backfill_historical_odds.py --env prod --api-key YOUR_API_KEY
"""
import argparse
import os
import time
from datetime import datetime, timedelta
from typing import Dict

import boto3
import requests

# Sports to backfill
SPORTS = [
    "basketball_nba",
    "americanfootball_nfl",
    "icehockey_nhl",
    "baseball_mlb",
    "soccer_epl",
]

# Markets to fetch
MARKETS = "h2h,spreads,totals"
REGIONS = "us"


class HistoricalOddsBackfill:
    def __init__(self, api_key: str, environment: str):
        self.api_key = api_key
        self.environment = environment
        self.base_url = "https://api.the-odds-api.com/v4/historical"

        # Set up DynamoDB
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        table_name = f"carpool-bets-v2-{environment}"
        self.table = self.dynamodb.Table(table_name)

        self.requests_used = 0
        self.games_stored = 0

    def backfill_sport(self, sport: str, start_date: datetime, end_date: datetime):
        """Backfill historical odds for a sport"""
        print(f"\n{'='*60}")
        print(f"Backfilling {sport}")
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print(f"{'='*60}")

        current_date = start_date

        # Fetch snapshots every 24 hours (one per day at noon)
        while current_date <= end_date:
            timestamp = (
                current_date.replace(hour=12, minute=0, second=0).isoformat() + "Z"
            )

            try:
                data = self._fetch_historical_odds(sport, timestamp)

                if data and "data" in data:
                    games = data["data"]
                    print(f"  {timestamp}: Found {len(games)} games")

                    for game in games:
                        self._store_game(game, sport)

                    self.games_stored += len(games)
                else:
                    print(f"  {timestamp}: No data")

                # Rate limiting - wait 1 second between requests
                time.sleep(1)

            except Exception as e:
                print(f"  {timestamp}: Error - {e}")

            # Move to next day
            current_date += timedelta(days=1)

    def _fetch_historical_odds(self, sport: str, timestamp: str) -> Dict:
        """Fetch historical odds for a specific timestamp"""
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            "apiKey": self.api_key,
            "regions": REGIONS,
            "markets": MARKETS,
            "oddsFormat": "american",
            "date": timestamp,
        }

        response = requests.get(url, params=params)
        self.requests_used += 1

        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            raise Exception("Invalid API key")
        elif response.status_code == 429:
            raise Exception("Rate limit exceeded")
        else:
            print(f"    API Error: {response.status_code} - {response.text}")
            return {}

    def _store_game(self, game: Dict, sport: str):
        """Store game odds in DynamoDB"""
        game_id = game.get("id")
        home_team = game.get("home_team")
        away_team = game.get("away_team")
        commence_time = game.get("commence_time")

        # Store each bookmaker's odds
        for bookmaker in game.get("bookmakers", []):
            bookmaker_key = bookmaker.get("key")

            for market in bookmaker.get("markets", []):
                market_key = market.get("key")

                item = {
                    "PK": f"GAME#{sport}#{game_id}",
                    "SK": f"ODDS#{bookmaker_key}#{market_key}",
                    "GSI1PK": f"SPORT#{sport}",
                    "GSI1SK": commence_time,
                    "game_id": game_id,
                    "sport": sport,
                    "home_team": home_team,
                    "away_team": away_team,
                    "commence_time": commence_time,
                    "bookmaker": bookmaker_key,
                    "market_key": market_key,
                    "outcomes": market.get("outcomes", []),
                    "last_update": bookmaker.get("last_update"),
                    "historical_backfill": True,
                    "backfill_date": datetime.utcnow().isoformat(),
                }

                try:
                    self.table.put_item(Item=item)
                except Exception as e:
                    print(f"    Error storing game {game_id}: {e}")

    def run(self, years_back: int = 2):
        """Run backfill for all sports"""
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=365 * years_back)

        print("\n" + "=" * 60)
        print("Historical Odds Backfill")
        print(f"Environment: {self.environment}")
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print(f"Sports: {', '.join(SPORTS)}")
        print("=" * 60)

        start_time = time.time()

        for sport in SPORTS:
            self.backfill_sport(sport, start_date, end_date)

        elapsed = time.time() - start_time

        print("\n" + "=" * 60)
        print("Backfill Complete!")
        print("=" * 60)
        print(f"Total API requests: {self.requests_used}")
        print(f"Total games stored: {self.games_stored}")
        print(f"Time elapsed: {elapsed / 60:.1f} minutes")
        print(f"Estimated cost: ${self.requests_used * 0.01:.2f}")
        print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Backfill historical odds data")
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "beta", "prod"],
        help="Environment to backfill",
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="The Odds API key",
    )
    parser.add_argument(
        "--years",
        type=int,
        default=2,
        help="Number of years to backfill (default: 2)",
    )
    parser.add_argument(
        "--profile",
        default=None,
        help="AWS profile to use (default: sports-betting-{env})",
    )

    args = parser.parse_args()

    # Set AWS profile
    profile = args.profile or f"sports-betting-{args.env}"
    os.environ["AWS_PROFILE"] = profile

    print(f"Using AWS profile: {profile}")

    # Run backfill
    backfill = HistoricalOddsBackfill(args.api_key, args.env)
    backfill.run(years_back=args.years)


if __name__ == "__main__":
    main()
