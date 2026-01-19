"""
Player Stats Collector - Fetches actual player statistics from ESPN API
"""

import os
import boto3
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal


class PlayerStatsCollector:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))
        self.espn_base_url = "https://site.web.api.espn.com/apis/site/v2/sports"

    def collect_stats_for_sport(self, sport: str) -> int:
        """Collect player stats for completed games"""
        if sport not in ["basketball_nba", "americanfootball_nfl"]:
            print(f"Player stats not supported for {sport}")
            return 0

        # Get completed games from DynamoDB
        completed_games = self._get_completed_games(sport)
        print(f"Found {len(completed_games)} completed games for {sport}")

        stats_collected = 0
        for game in completed_games:
            try:
                # Get ESPN game ID by matching teams and date
                espn_game_id = self._find_espn_game_id(game, sport)

                if espn_game_id:
                    # Fetch player stats from ESPN
                    player_stats = self._fetch_espn_player_stats(espn_game_id, sport)

                    if player_stats:
                        # Store stats in DynamoDB
                        self._store_player_stats(game["id"], player_stats, sport)
                        stats_collected += len(player_stats)
                        print(
                            f"Stored stats for {len(player_stats)} players in game {game['id']}"
                        )
                else:
                    print(f"Could not find ESPN game ID for {game['id']}")

            except Exception as e:
                print(f"Error collecting stats for game {game['id']}: {e}")
                continue

        return stats_collected

    def _get_completed_games(self, sport: str) -> List[Dict[str, Any]]:
        """Get completed games that don't have player stats yet"""
        try:
            # Query using GSI to get games by commence_time
            now = datetime.now(timezone.utc)
            two_hours_ago = (now - timedelta(hours=2)).isoformat()

            response = self.table.query(
                IndexName="ActiveBetsIndexV2",
                KeyConditionExpression="active_bet_pk = :pk AND commence_time < :now",
                FilterExpression="contains(sk, :latest) AND attribute_not_exists(player_stats_collected)",
                ExpressionAttributeValues={
                    ":pk": f"GAME#{sport}",
                    ":now": two_hours_ago,
                    ":latest": "LATEST",
                },
                ProjectionExpression="pk, home_team, away_team, commence_time",
            )

            # Deduplicate by game_id (pk)
            seen_games = set()
            games = []
            for item in response.get("Items", []):
                game_id = item["pk"].split("#")[1]
                if game_id not in seen_games:
                    seen_games.add(game_id)
                    games.append(
                        {
                            "id": game_id,
                            "home_team": item.get("home_team"),
                            "away_team": item.get("away_team"),
                            "commence_time": item.get("commence_time"),
                        }
                    )

            return games

        except Exception as e:
            print(f"Error getting completed games: {e}")
            return []

    def _find_espn_game_id(self, game: Dict[str, Any], sport: str) -> Optional[str]:
        """Find ESPN game ID by matching teams and date"""
        try:
            # Convert sport key to ESPN format
            espn_sport = (
                "basketball/nba" if sport == "basketball_nba" else "football/nfl"
            )

            # Get game date (YYYYMMDD format)
            game_date = datetime.fromisoformat(
                game["commence_time"].replace("Z", "+00:00")
            )
            date_str = game_date.strftime("%Y%m%d")

            print(
                f"Looking for game on {date_str}: {game['home_team']} vs {game['away_team']}"
            )

            # Fetch scoreboard for that date
            url = f"{self.espn_base_url}/{espn_sport}/scoreboard?dates={date_str}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            events = data.get("events", [])
            print(f"Found {len(events)} ESPN events on {date_str}")

            # Match by team names
            our_teams = {game["home_team"], game["away_team"]}

            for event in events:
                competitions = event.get("competitions", [])
                if not competitions:
                    continue

                competition = competitions[0]
                competitors = competition.get("competitors", [])

                if len(competitors) >= 2:
                    team_names = {
                        c.get("team", {}).get("displayName", "") for c in competitors
                    }

                    # Check if both teams match
                    if team_names == our_teams:
                        print(f"Match found! ESPN game ID: {event.get('id')}")
                        return event.get("id")

            # If not found, try previous day (for late night games)
            prev_date = game_date - timedelta(days=1)
            prev_date_str = prev_date.strftime("%Y%m%d")
            print(f"Not found on {date_str}, trying {prev_date_str}")

            url = f"{self.espn_base_url}/{espn_sport}/scoreboard?dates={prev_date_str}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            events = data.get("events", [])
            print(f"Found {len(events)} ESPN events on {prev_date_str}")

            for event in events:
                competitions = event.get("competitions", [])
                if not competitions:
                    continue

                competition = competitions[0]
                competitors = competition.get("competitors", [])

                if len(competitors) >= 2:
                    team_names = {
                        c.get("team", {}).get("displayName", "") for c in competitors
                    }

                    # Check if both teams match
                    if team_names == our_teams:
                        print(f"Match found! ESPN game ID: {event.get('id')}")
                        return event.get("id")

            return None

        except Exception as e:
            print(f"Error finding ESPN game ID: {e}")
            return None

    def _fetch_espn_player_stats(
        self, espn_game_id: str, sport: str
    ) -> List[Dict[str, Any]]:
        """Fetch player stats from ESPN API"""
        try:
            espn_sport = (
                "basketball/nba" if sport == "basketball_nba" else "football/nfl"
            )
            url = f"{self.espn_base_url}/{espn_sport}/summary?event={espn_game_id}"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            boxscore = data.get("boxscore", {})
            players = boxscore.get("players", [])

            all_player_stats = []

            for team_data in players:
                team_name = team_data.get("team", {}).get("displayName", "")
                statistics = team_data.get("statistics", [])

                for stat_group in statistics:
                    for athlete in stat_group.get("athletes", []):
                        player_name = athlete.get("athlete", {}).get("displayName", "")
                        stats = athlete.get("stats", [])

                        # Parse stats into dict
                        stat_dict = {
                            "player_name": player_name,
                            "team": team_name,
                        }

                        # Map stat names to values
                        stat_names = stat_group.get("names", [])
                        for i, stat_value in enumerate(stats):
                            if i < len(stat_names):
                                stat_dict[stat_names[i]] = stat_value

                        all_player_stats.append(stat_dict)

            return all_player_stats

        except Exception as e:
            print(f"Error fetching ESPN player stats: {e}")
            return []

    def _store_player_stats(
        self, game_id: str, player_stats: List[Dict[str, Any]], sport: str
    ):
        """Store player stats in DynamoDB"""
        try:
            for stats in player_stats:
                player_name = stats.get("player_name")
                if not player_name:
                    continue

                # Convert float values to Decimal
                stats_decimal = self._convert_to_decimal(stats)

                pk = f"PLAYER_STATS#{sport}#{game_id}#{player_name}"
                sk = "LATEST"

                self.table.put_item(
                    Item={
                        "pk": pk,
                        "sk": sk,
                        "game_id": game_id,
                        "sport": sport,
                        "player_name": player_name,
                        "stats": stats_decimal,
                        "collected_at": datetime.utcnow().isoformat(),
                    }
                )

            # Mark game as having stats collected
            self.table.update_item(
                Key={"pk": f"GAME#{sport}#{game_id}", "sk": "LATEST"},
                UpdateExpression="SET player_stats_collected = :true",
                ExpressionAttributeValues={":true": True},
            )

        except Exception as e:
            print(f"Error storing player stats: {e}")

    def _convert_to_decimal(self, obj):
        """Convert float values to Decimal for DynamoDB"""
        if isinstance(obj, float):
            return Decimal(str(obj))
        elif isinstance(obj, dict):
            return {k: self._convert_to_decimal(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convert_to_decimal(v) for v in obj]
        return obj


def lambda_handler(event, context):
    """AWS Lambda handler for player stats collection"""
    try:
        collector = PlayerStatsCollector()
        sport = event.get("sport", "basketball_nba")

        stats_collected = collector.collect_stats_for_sport(sport)

        return {
            "statusCode": 200,
            "body": {
                "message": f"Collected stats for {stats_collected} players",
                "sport": sport,
                "stats_collected": stats_collected,
            },
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"error": str(e)},
        }


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    collector = PlayerStatsCollector()
    collector.collect_stats_for_sport("basketball_nba")
