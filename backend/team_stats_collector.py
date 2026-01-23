"""
Team Stats Collector - Fetches actual team statistics from ESPN API
"""

import os
import boto3
import requests
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal


class TeamStatsCollector:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))
        self.espn_base_url = "https://site.web.api.espn.com/apis/site/v2/sports"

    def collect_stats_for_sport(self, sport: str) -> int:
        """Collect team stats for completed games"""
        if sport not in ["basketball_nba", "americanfootball_nfl"]:
            print(f"Team stats not supported for {sport}")
            return 0

        # Get completed games from DynamoDB
        completed_games = self._get_completed_games(sport)
        print(f"Found {len(completed_games)} completed games for {sport}")

        games_processed = 0
        for game in completed_games:
            try:
                # Get ESPN game ID by matching teams and date
                espn_game_id = self._find_espn_game_id(game, sport)

                if espn_game_id:
                    # Fetch team stats from ESPN
                    team_stats = self._fetch_espn_team_stats(espn_game_id, sport)

                    if team_stats:
                        # Store stats in DynamoDB
                        self._store_team_stats(game["id"], team_stats, sport)
                        games_processed += 1
                        print(f"Stored team stats for game {game['id']}")
                else:
                    print(f"Could not find ESPN game ID for {game['id']}")

            except Exception as e:
                print(f"Error collecting stats for game {game['id']}: {e}")
                continue

        return games_processed

    def _get_completed_games(self, sport: str) -> List[Dict[str, Any]]:
        """Get completed games that don't have team stats yet"""
        try:
            # Query using GSI to get games by commence_time
            now = datetime.now(timezone.utc)
            two_hours_ago = (now - timedelta(hours=2)).isoformat()

            response = self.table.query(
                IndexName="ActiveBetsIndexV2",
                KeyConditionExpression="active_bet_pk = :pk AND commence_time < :now",
                FilterExpression="contains(sk, :latest) AND attribute_not_exists(team_stats_collected)",
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

            # Fetch scoreboard for that date
            url = f"{self.espn_base_url}/{espn_sport}/scoreboard?dates={date_str}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            events = data.get("events", [])

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
                        return event.get("id")

            # If not found, try previous day (for late night games)
            prev_date = game_date - timedelta(days=1)
            prev_date_str = prev_date.strftime("%Y%m%d")

            url = f"{self.espn_base_url}/{espn_sport}/scoreboard?dates={prev_date_str}"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            events = data.get("events", [])

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
                        return event.get("id")

            return None

        except Exception as e:
            print(f"Error finding ESPN game ID: {e}")
            return None

    def _fetch_espn_team_stats(
        self, espn_game_id: str, sport: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch team stats from ESPN API"""
        try:
            espn_sport = (
                "basketball/nba" if sport == "basketball_nba" else "football/nfl"
            )
            url = f"{self.espn_base_url}/{espn_sport}/summary?event={espn_game_id}"

            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            boxscore = data.get("boxscore", {})
            teams = boxscore.get("teams", [])

            if not teams:
                return None

            team_stats = {}
            for team in teams:
                team_name = team.get("team", {}).get("displayName", "")
                statistics = team.get("statistics", [])

                stats_dict = {}
                for stat in statistics:
                    label = stat.get("label", "")
                    value = stat.get("displayValue", "")
                    stats_dict[label] = value

                team_stats[team_name] = stats_dict

            return team_stats if team_stats else None

        except Exception as e:
            print(f"Error fetching ESPN team stats: {e}")
            return None

    def _store_team_stats(
        self, game_id: str, team_stats: Dict[str, Any], sport: str
    ) -> None:
        """Store team stats in DynamoDB"""
        try:
            # Convert to Decimal for DynamoDB
            team_stats_decimal = self._convert_to_decimal(team_stats)

            # Store team stats as separate records
            for team_name, stats in team_stats_decimal.items():
                pk = f"TEAM_STATS#{sport}#{team_name}"
                sk = game_id

                self.table.put_item(
                    Item={
                        "pk": pk,
                        "sk": sk,
                        "game_id": game_id,
                        "sport": sport,
                        "team_name": team_name,
                        "stats": stats,
                        "collected_at": datetime.utcnow().isoformat(),
                    }
                )

        except Exception as e:
            print(f"Error storing team stats: {e}")

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
    """AWS Lambda handler for team stats collection"""
    try:
        collector = TeamStatsCollector()
        sport = event.get("sport", "basketball_nba")

        games_processed = collector.collect_stats_for_sport(sport)

        return {
            "statusCode": 200,
            "body": {
                "message": f"Collected team stats for {games_processed} games",
                "sport": sport,
                "games_processed": games_processed,
            },
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {"statusCode": 500, "body": {"error": str(e)}}


if __name__ == "__main__":
    from dotenv import load_dotenv

    load_dotenv()

    collector = TeamStatsCollector()
    collector.collect_stats_for_sport("basketball_nba")
