import os
import boto3
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor, as_completed


def get_secret(secret_arn: str) -> str:
    """Retrieve secret from AWS Secrets Manager"""
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId=secret_arn)
    return response["SecretString"]


def convert_floats_to_decimal(obj):
    """Convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    return obj


class OddsCollector:
    def __init__(self):
        from dao import BettingDAO

        secret_arn = os.getenv("ODDS_API_SECRET_ARN")
        if secret_arn:
            self.api_key = get_secret(secret_arn)
        else:
            self.api_key = os.getenv("ODDS_API_KEY")  # Fallback for local testing

        self.base_url = "https://api.the-odds-api.com/v4"
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))
        self.dao = BettingDAO()

    def get_active_sports(self) -> List[str]:
        """Get sports currently in season"""
        url = f"{self.base_url}/sports"
        params = {"api_key": self.api_key}

        response = requests.get(url, params=params)
        response.raise_for_status()

        sports = response.json()
        # Filter for active sports (NFL, NBA, MLB, NHL, EPL, MLS)
        active = [
            sport["key"]
            for sport in sports
            if sport["active"]
            and sport["key"]
            in [
                "americanfootball_nfl",
                "basketball_nba",
                "baseball_mlb",
                "icehockey_nhl",
                "soccer_epl",
                "soccer_usa_mls",
                "mma_mixed_martial_arts",
                "boxing_boxing",
            ]
        ]
        return active

    def get_odds(self, sport: str, limit: int = None) -> List[Dict[str, Any]]:
        """Get odds for a specific sport"""
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            "api_key": self.api_key,
            "regions": "us",
            "markets": "h2h,spreads,totals",
            "oddsFormat": "american",
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        odds = response.json()

        # Apply limit if specified
        if limit and limit > 0:
            odds = odds[:limit]
            print(f"Limited to {len(odds)} games for testing")

        return odds

    def get_player_props(self, sport: str, event_id: str) -> List[Dict[str, Any]]:
        """Get player props for a specific event"""
        url = f"{self.base_url}/sports/{sport}/events/{event_id}/odds"
        params = {
            "api_key": self.api_key,
            "regions": "us",
            "markets": "player_pass_tds,player_pass_yds,player_rush_yds,player_receptions,player_reception_yds,player_points,player_rebounds,player_assists",
            "oddsFormat": "american",
        }

        response = requests.get(url, params=params)
        response.raise_for_status()

        return response.json()

    def store_player_props(self, sport: str, event_id: str, props_data: Dict[str, Any]):
        """Store player props in DynamoDB with smart updating - only create new records if data changed"""

        for bookmaker in props_data.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                for outcome in market.get("outcomes", []):
                    # Extract player name from outcome description
                    player_name = outcome.get("description", "Unknown")

                    pk = f"PROP#{event_id}#{player_name}"
                    sk_latest = (
                        f"{bookmaker['key']}#{market['key']}#{outcome['name']}#LATEST"
                    )

                    # Check if latest record exists and if data has changed
                    try:
                        existing_response = self.table.get_item(
                            Key={"pk": pk, "sk": sk_latest}
                        )
                        existing_item = existing_response.get("Item")

                        # Compare key prop data to see if it changed
                        new_point = convert_floats_to_decimal(outcome.get("point"))
                        new_price = convert_floats_to_decimal(outcome["price"])
                        data_changed = True

                        if existing_item:
                            existing_point = existing_item.get("point")
                            existing_price = existing_item.get("price")
                            data_changed = (new_point != existing_point) or (
                                new_price != existing_price
                            )

                        timestamp = datetime.utcnow().isoformat()
                        commence_dt = datetime.fromisoformat(
                            props_data["commence_time"].replace("Z", "+00:00")
                        )
                        ttl = int((commence_dt + timedelta(days=2)).timestamp())

                        item_data = {
                            "pk": pk,
                            "sport": sport,
                            "event_id": event_id,
                            "bookmaker": bookmaker["key"],
                            "market_key": market["key"],
                            "player_name": player_name,
                            "outcome": outcome["name"],  # "Over" or "Under"
                            "point": new_point,
                            "price": new_price,
                            "commence_time": props_data["commence_time"],
                            "updated_at": timestamp,
                            "ttl": ttl,
                        }

                        if data_changed:
                            # Store historical snapshot with new timestamp (no active_bet_pk)
                            sk_historical = f"{bookmaker['key']}#{market['key']}#{outcome['name']}#{timestamp}"
                            self.table.put_item(Item={**item_data, "sk": sk_historical})

                            # Update latest pointer with new data, timestamp, and sparse index key
                            latest_item = {
                                **item_data,
                                "sk": sk_latest,
                                "latest": True,
                                "active_bet_pk": f"PROP#{sport}",
                            }
                            self.table.put_item(Item=latest_item)
                        else:
                            # Data unchanged, just update timestamp on existing LATEST record
                            self.table.update_item(
                                Key={"pk": pk, "sk": sk_latest},
                                UpdateExpression="SET updated_at = :timestamp, active_bet_pk = :active_pk",
                                ExpressionAttributeValues={
                                    ":timestamp": timestamp,
                                    ":active_pk": f"PROP#{sport}",
                                },
                            )

                    except Exception as e:
                        print(f"Error processing props for {event_id}: {str(e)}")
                        continue

    def store_odds(self, sport: str, odds_data: List[Dict[str, Any]]):
        """Store odds in DynamoDB with smart updating - only create new records if data changed"""

        for game in odds_data:
            game_id = game["id"]

            for bookmaker in game["bookmakers"]:
                for market in bookmaker["markets"]:
                    pk = f"GAME#{game_id}"
                    sk_latest = f"{bookmaker['key']}#{market['key']}#LATEST"

                    # Check if latest record exists and if data has changed
                    try:
                        existing_response = self.table.get_item(
                            Key={"pk": pk, "sk": sk_latest}
                        )
                        existing_item = existing_response.get("Item")

                        # Compare outcomes to see if odds changed
                        new_outcomes = convert_floats_to_decimal(market["outcomes"])
                        data_changed = True

                        if existing_item:
                            existing_outcomes = existing_item.get("outcomes", [])
                            data_changed = new_outcomes != existing_outcomes

                        timestamp = datetime.utcnow().isoformat()
                        commence_dt = datetime.fromisoformat(
                            game["commence_time"].replace("Z", "+00:00")
                        )
                        ttl = int((commence_dt + timedelta(days=2)).timestamp())

                        item_data = {
                            "pk": pk,
                            "sport": sport,
                            "home_team": game["home_team"],
                            "away_team": game["away_team"],
                            "commence_time": game["commence_time"],
                            "market_key": market["key"],
                            "bookmaker": bookmaker["key"],
                            "outcomes": new_outcomes,
                            "updated_at": timestamp,
                            "ttl": ttl,
                        }

                        if data_changed:
                            print(
                                f"Data changed for {pk} {sk_latest} - creating new records"
                            )
                            # Store historical snapshot with new timestamp (no active_bet_pk)
                            sk_historical = (
                                f"{bookmaker['key']}#{market['key']}#{timestamp}"
                            )
                            self.table.put_item(Item={**item_data, "sk": sk_historical})

                            # Update latest pointer with new data, timestamp, and sparse index key
                            latest_item = {
                                **item_data,
                                "sk": sk_latest,
                                "latest": True,
                                "active_bet_pk": f"GAME#{sport}",
                            }
                            self.table.put_item(Item=latest_item)
                            print(
                                f"Created historical record {sk_historical} and updated LATEST"
                            )
                        else:
                            print(
                                f"Data unchanged for {pk} {sk_latest} - updating timestamp to {timestamp}"
                            )
                            # Data unchanged, just update timestamp on existing LATEST record
                            response = self.table.update_item(
                                Key={"pk": pk, "sk": sk_latest},
                                UpdateExpression="SET updated_at = :timestamp, active_bet_pk = :active_pk",
                                ExpressionAttributeValues={
                                    ":timestamp": timestamp,
                                    ":active_pk": f"GAME#{sport}",
                                },
                                ReturnValues="ALL_NEW",
                            )
                            print(
                                f"Updated timestamp: {response.get('Attributes', {}).get('updated_at', 'FAILED')}"
                            )

                    except Exception as e:
                        print(f"Error processing odds for {game_id}: {str(e)}")
                        continue

    def collect_props_for_sport(self, sport: str, limit: int = None) -> int:
        """Collect player props for a sport using existing game data with parallel processing"""
        if sport not in ["basketball_nba", "americanfootball_nfl"]:
            print(f"Player props not supported for {sport}")
            return 0

        game_ids = self.dao.get_game_ids_from_db(sport)
        if not game_ids:
            print(f"No games found in DB for {sport}")
            return 0

        # Apply limit if specified
        if limit and limit > 0:
            game_ids = game_ids[:limit]
            print(f"Limited to {len(game_ids)} games for testing")

        print(
            f"Found {len(game_ids)} games for {sport}, collecting props in parallel..."
        )
        total_props = 0

        def collect_props_for_game(game_id):
            """Helper function to collect props for a single game"""
            try:
                props = self.get_player_props(sport, game_id)
                if props.get("bookmakers"):
                    self.store_player_props(sport, game_id, props)
                    return len(props.get("bookmakers", []))
                return 0
            except Exception as e:
                print(f"Error collecting props for game {game_id}: {str(e)}")
                return 0

        # Use ThreadPoolExecutor for parallel API calls
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_to_game = {
                executor.submit(collect_props_for_game, game_id): game_id
                for game_id in game_ids
            }

            for future in as_completed(future_to_game):
                game_id = future_to_game[future]
                try:
                    props_count = future.result()
                    total_props += props_count
                    print(
                        f"Completed props collection for game {game_id}: {props_count} bookmakers"
                    )
                except Exception as e:
                    print(f"Game {game_id} generated an exception: {str(e)}")

        print(f"Collected {total_props} player prop bookmakers for {sport}")
        return total_props

    def collect_odds_for_sport(self, sport: str, limit: int = None) -> int:
        """Collect odds for a specific sport (odds only, no props)"""
        try:
            print(f"Collecting odds for {sport}...")
            odds = self.get_odds(sport, limit=limit)
            if odds:
                self.store_odds(sport, odds)
                print(f"Stored {len(odds)} games for {sport}")
                return len(odds)
            else:
                print(f"No odds available for {sport}")
                return 0
        except Exception as e:
            print(f"Error collecting odds for {sport}: {str(e)}")
            return 0

    def collect_all_odds(self):
        """Main method to collect odds for all active sports"""
        active_sports = self.get_active_sports()
        print(f"Active sports: {active_sports}")

        total_games = 0
        for sport in active_sports:
            total_games += self.collect_odds_for_sport(sport)

        return total_games


def lambda_handler(event, context):
    """AWS Lambda handler - supports multiple execution modes:
    - {"sport": "basketball_nba"} - collect odds only for NBA
    - {"sport": "basketball_nba", "props_only": true} - collect NBA props with parallel processing
    - {"limit": 5} - limit number of games/props for testing
    - {} - collect odds for all sports (no props)
    """
    try:
        collector = OddsCollector()

        # Parse event parameters
        sport = event.get("sport") if event else None
        props_only = event.get("props_only", False) if event else False
        limit = event.get("limit") if event else None

        if sport and props_only:
            print(f"Processing props only for: {sport} (limit: {limit})")
            total_props = collector.collect_props_for_sport(sport, limit=limit)
            message = (
                f"Successfully collected props for {total_props} bookmakers in {sport}"
            )
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "message": message,
                        "sport": sport,
                        "props_only": True,
                        "props_collected": total_props,
                        "limit": limit,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                ),
            }
        elif sport:
            print(f"Processing odds only for: {sport} (limit: {limit})")
            total_games = collector.collect_odds_for_sport(sport, limit=limit)
            message = f"Successfully collected odds for {total_games} games in {sport}"
        else:
            print("Processing all active sports (odds only)")
            total_games = collector.collect_all_odds()
            message = f"Successfully collected odds for {total_games} total games"

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": message,
                    "sport": sport,
                    "props_only": False,
                    "games_collected": total_games,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps(
                {
                    "error": str(e),
                    "sport": sport if "sport" in locals() else None,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            ),
        }


if __name__ == "__main__":
    # For local testing
    from dotenv import load_dotenv

    load_dotenv()
    collector = OddsCollector()
    collector.collect_all_odds()
