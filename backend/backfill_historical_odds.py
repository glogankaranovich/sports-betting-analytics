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
import json
import os
import time
from datetime import datetime, timedelta
from decimal import Decimal
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
        self.outcomes_stored = 0

    def backfill_sport(self, sport: str, start_date: datetime, end_date: datetime):
        """Backfill historical odds and outcomes for a sport"""
        print(f"\n{'='*60}")
        print(f"Backfilling {sport}")
        print(f"Date range: {start_date.date()} to {end_date.date()}")
        print(f"{'='*60}")

        current_date = start_date
        game_ids = set()

        # Fetch snapshots every 24 hours (one per day at noon)
        while current_date <= end_date:
            timestamp = current_date.replace(
                hour=12, minute=0, second=0, microsecond=0
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

            try:
                data = self._fetch_historical_odds(sport, timestamp)

                if data and "data" in data:
                    games = data["data"]
                    print(f"  {timestamp}: Found {len(games)} games")

                    for game in games:
                        self._store_game(game, sport)
                        game_ids.add(game.get("id"))

                    self.games_stored += len(games)
                else:
                    print(f"  {timestamp}: No data")

                # Rate limiting - wait 1 second between requests
                time.sleep(1)

            except Exception as e:
                print(f"  {timestamp}: Error - {e}")

            # Move to next day
            current_date += timedelta(days=1)

        # After odds backfill, fetch outcomes for completed games
        print(f"\n  Fetching outcomes for {len(game_ids)} games...")
        self._backfill_outcomes(sport, start_date, end_date)

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
        """Store game odds in DynamoDB with HISTORICAL prefix"""
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
                    "pk": f"HISTORICAL#{sport}#{game_id}",
                    "sk": f"ODDS#{bookmaker_key}#{market_key}",
                    "game_index_pk": game_id,
                    "game_index_sk": f"ODDS#{bookmaker_key}#{market_key}",
                    "analysis_time_pk": f"HISTORICAL#{sport}",
                    "game_id": game_id,
                    "sport": sport,
                    "home_team": home_team,
                    "away_team": away_team,
                    "commence_time": commence_time,
                    "bookmaker": bookmaker_key,
                    "market_key": market_key,
                    "outcomes": json.loads(
                        json.dumps(market.get("outcomes", [])), parse_float=Decimal
                    ),
                    "last_update": bookmaker.get("last_update"),
                }

                try:
                    self.table.put_item(Item=item)
                except Exception as e:
                    print(f"    Error storing game {game_id}: {e}")

    def _backfill_outcomes(self, sport: str, start_date: datetime, end_date: datetime):
        """Fetch and store outcomes for completed games using ESPN API"""
        try:
            # Map our sport keys to ESPN API format
            espn_sport_map = {
                "basketball_nba": ("basketball", "nba"),
                "americanfootball_nfl": ("football", "nfl"),
                "icehockey_nhl": ("hockey", "nhl"),
                "baseball_mlb": ("baseball", "mlb"),
                "soccer_epl": ("soccer", "eng.1"),
            }

            if sport not in espn_sport_map:
                print(f"  ESPN API not supported for {sport}")
                return

            espn_sport, espn_league = espn_sport_map[sport]

            # Fetch outcomes day by day
            current_date = start_date
            while current_date <= end_date:
                date_str = current_date.strftime("%Y%m%d")

                try:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/{espn_sport}/{espn_league}/scoreboard"
                    params = {"dates": date_str}

                    response = requests.get(url, params=params, timeout=10)

                    if response.status_code != 200:
                        current_date += timedelta(days=1)
                        continue

                    data = response.json()
                    events = data.get("events", [])

                    for event in events:
                        if (
                            event.get("status", {}).get("type", {}).get("completed")
                            is not True
                        ):
                            continue

                        competitions = event.get("competitions", [])
                        if not competitions:
                            continue

                        competition = competitions[0]
                        competitors = competition.get("competitors", [])

                        if len(competitors) < 2:
                            continue

                        # Find home and away teams
                        home_team = None
                        away_team = None
                        home_score = None
                        away_score = None

                        for competitor in competitors:
                            team_name = competitor.get("team", {}).get("displayName")
                            score = competitor.get("score")

                            if competitor.get("homeAway") == "home":
                                home_team = team_name
                                home_score = score
                            else:
                                away_team = team_name
                                away_score = score

                        if not all([home_team, away_team, home_score, away_score]):
                            continue

                        # Determine winner
                        home_score_num = float(home_score)
                        away_score_num = float(away_score)
                        winner = (
                            home_team if home_score_num > away_score_num else away_team
                        )

                        espn_event_id = event.get("id")
                        commence_time = event.get("date")

                        # Store with ESPN ID - will need to match to Odds API game_id later
                        item = {
                            "pk": f"HISTORICAL#{sport}#ESPN_{espn_event_id}",
                            "sk": "OUTCOME",
                            "game_index_pk": f"ESPN_{espn_event_id}",
                            "game_index_sk": "OUTCOME",
                            "analysis_time_pk": f"HISTORICAL#{sport}",
                            "sport": sport,
                            "home_team": home_team,
                            "away_team": away_team,
                            "commence_time": commence_time,
                            "home_score": Decimal(str(home_score_num)),
                            "away_score": Decimal(str(away_score_num)),
                            "winner": winner,
                            "espn_event_id": espn_event_id,
                        }

                        try:
                            self.table.put_item(Item=item)
                            self.outcomes_stored += 1
                        except Exception as e:
                            print(f"    Error storing outcome: {e}")

                    time.sleep(0.5)  # Rate limiting

                except Exception as e:
                    print(f"    Error for {date_str}: {e}")

                current_date += timedelta(days=1)

            print(f"  Stored {self.outcomes_stored} outcomes from ESPN")

        except Exception as e:
            print(f"  Error in ESPN outcome collection: {e}")

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
        print(f"Total outcomes stored: {self.outcomes_stored}")
        print(f"Time elapsed: {elapsed / 60:.1f} minutes")
        print(f"Estimated cost: ${self.requests_used * 0.01:.2f}")
        print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Backfill historical odds data")
    parser.add_argument(
        "--env",
        required=True,
        choices=["dev", "beta", "staging", "prod"],
        help="Environment to backfill",
    )
    parser.add_argument(
        "--api-key",
        required=True,
        help="The Odds API key",
    )
    parser.add_argument(
        "--years",
        type=float,
        default=2,
        help="Number of years to backfill (default: 2, can be decimal like 0.083 for 1 month)",
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
