"""
Schedule Data Collector
Fetches team schedules from ESPN API and stores in DynamoDB
"""
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3
import requests

dynamodb = boto3.resource("dynamodb")
table = dynamodb.Table(os.environ.get("DYNAMODB_TABLE", "sports-betting-bets-dev"))


class ScheduleCollector:
    def __init__(self):
        self.espn_base_url = "https://site.api.espn.com/apis/site/v2/sports"
        self.table = table

    def collect_schedules_for_sport(self, sport: str) -> int:
        """Collect schedules for all teams in a sport"""
        teams = self._get_teams(sport)
        schedules_collected = 0

        for team in teams:
            team_id = team.get("id")
            team_name = team.get("displayName", "").lower().replace(" ", "_")

            schedule = self._fetch_team_schedule(sport, team_id)
            if schedule:
                self._store_schedule(sport, team_name, schedule)
                schedules_collected += 1

        return schedules_collected

    def _get_teams(self, sport: str) -> List[Dict[str, Any]]:
        """Get all teams for a sport"""
        sport_map = {
            "basketball_nba": "basketball/nba",
            "americanfootball_nfl": "football/nfl",
            "baseball_mlb": "baseball/mlb",
            "icehockey_nhl": "hockey/nhl",
            "soccer_epl": "soccer/eng.1",
        }
        espn_sport = sport_map.get(sport, "basketball/nba")

        try:
            url = f"{self.espn_base_url}/{espn_sport}/teams"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            teams = []
            for league in data.get("sports", [{}])[0].get("leagues", []):
                teams.extend(league.get("teams", []))

            return [t.get("team", {}) for t in teams]
        except Exception as e:
            print(f"Error fetching teams: {e}")
            return []

    def _fetch_team_schedule(
        self, sport: str, team_id: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Fetch schedule for a specific team"""
        sport_map = {
            "basketball_nba": "basketball/nba",
            "americanfootball_nfl": "football/nfl",
            "baseball_mlb": "baseball/mlb",
            "icehockey_nhl": "hockey/nhl",
            "soccer_epl": "soccer/eng.1",
        }
        espn_sport = sport_map.get(sport, "basketball/nba")

        try:
            url = f"{self.espn_base_url}/{espn_sport}/teams/{team_id}/schedule"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            events = data.get("events", [])

            schedule_items = []
            for event in events:
                game_date = event.get("date")
                competitions = event.get("competitions", [])

                if not competitions:
                    continue

                comp = competitions[0]
                competitors = comp.get("competitors", [])

                # Determine if home game
                is_home = False
                for competitor in competitors:
                    if competitor.get("id") == team_id:
                        is_home = competitor.get("homeAway") == "home"
                        break

                schedule_items.append(
                    {
                        "game_id": event.get("id"),
                        "game_date": game_date,
                        "is_home": is_home,
                        "opponent": self._get_opponent(competitors, team_id),
                    }
                )

            return schedule_items
        except Exception as e:
            print(f"Error fetching schedule for team {team_id}: {e}")
            return None

    def _get_opponent(self, competitors: List[Dict], team_id: str) -> str:
        """Get opponent team name"""
        for competitor in competitors:
            if competitor.get("id") != team_id:
                return competitor.get("team", {}).get("displayName", "Unknown")
        return "Unknown"

    def _store_schedule(
        self, sport: str, team_name: str, schedule: List[Dict[str, Any]]
    ):
        """Store schedule in DynamoDB"""
        # Sort by date
        sorted_schedule = sorted(schedule, key=lambda x: x["game_date"])

        # Calculate rest days
        for i, game in enumerate(sorted_schedule):
            rest_days = 0
            if i > 0:
                prev_date = datetime.fromisoformat(
                    sorted_schedule[i - 1]["game_date"].replace("Z", "+00:00")
                )
                curr_date = datetime.fromisoformat(
                    game["game_date"].replace("Z", "+00:00")
                )
                rest_days = (curr_date - prev_date).days - 1

            # Calculate TTL: 7 days after game date
            game_date = datetime.fromisoformat(game["game_date"].replace("Z", "+00:00"))
            ttl = int((game_date + timedelta(days=7)).timestamp())

            # Store in DynamoDB
            self.table.put_item(
                Item={
                    "pk": f"SCHEDULE#{sport}#{team_name}",
                    "sk": game["game_date"],
                    "game_id": game["game_id"],
                    "is_home": game["is_home"],
                    "opponent": game["opponent"],
                    "rest_days": rest_days,
                    "sport": sport,
                    "team": team_name,
                    "collected_at": datetime.utcnow().isoformat(),
                    "ttl": ttl,
                }
            )


def lambda_handler(event, context):
    """Lambda handler for schedule collection"""
    try:
        sport = event.get("sport", "basketball_nba")
        print(f"Collecting schedules for {sport}")

        collector = ScheduleCollector()
        count = collector.collect_schedules_for_sport(sport)

        return {"statusCode": 200, "body": {"schedules_collected": count, "sport": sport}}
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Emit CloudWatch metric
        try:
            import boto3
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.put_metric_data(
                Namespace='SportsAnalytics/ScheduleCollector',
                MetricData=[{
                    'MetricName': 'CollectionError',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {'Name': 'Sport', 'Value': event.get('sport', 'unknown') if event else 'unknown'}
                    ]
                }]
            )
        except:
            pass
        
        return {"statusCode": 500, "body": {"error": str(e)}}
