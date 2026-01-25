"""
Injury Collector - Fetches player injury reports from ESPN API
"""

import os
import boto3
import requests
from datetime import datetime, timezone
from typing import Dict, Any, List


class InjuryCollector:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))
        self.espn_base_url = "http://sports.core.api.espn.com/v2/sports"

    def collect_injuries_for_sport(self, sport: str) -> int:
        """Collect injury reports for all teams in a sport"""
        sport_mapping = {
            "basketball_nba": ("basketball", "nba"),
            "americanfootball_nfl": ("football", "nfl"),
            "baseball_mlb": ("baseball", "mlb"),
            "icehockey_nhl": ("hockey", "nhl"),
        }

        if sport not in sport_mapping:
            print(f"Injury collection not supported for {sport}")
            return 0

        espn_sport, league = sport_mapping[sport]
        teams = self._get_teams(espn_sport, league)

        injuries_collected = 0
        for team in teams:
            team_injuries = self._fetch_team_injuries(espn_sport, league, team["id"])
            if team_injuries:
                self._store_injuries(sport, team["id"], team["name"], team_injuries)
                injuries_collected += len(team_injuries)

        print(f"Collected {injuries_collected} injuries for {sport}")
        return injuries_collected

    def _get_teams(self, espn_sport: str, league: str) -> List[Dict[str, Any]]:
        """Get all teams for a sport"""
        url = f"{self.espn_base_url}/{espn_sport}/leagues/{league}/teams"
        try:
            response = requests.get(url, params={"limit": 100}, timeout=10)
            response.raise_for_status()
            data = response.json()

            teams = []
            for item in data.get("items", []):
                team_url = item.get("$ref")
                if team_url:
                    team_data = requests.get(team_url, timeout=10).json()
                    teams.append(
                        {
                            "id": team_data.get("id"),
                            "name": team_data.get("displayName"),
                        }
                    )
            return teams
        except Exception as e:
            print(f"Error fetching teams: {e}")
            return []

    def _fetch_team_injuries(
        self, espn_sport: str, league: str, team_id: str
    ) -> List[Dict[str, Any]]:
        """Fetch injury reports for a team"""
        url = f"{self.espn_base_url}/{espn_sport}/leagues/{league}/teams/{team_id}/injuries"
        try:
            response = requests.get(
                url, params={"lang": "en", "region": "us"}, timeout=10
            )
            response.raise_for_status()
            data = response.json()

            injuries = []
            for item in data.get("items", []):
                injury_url = item.get("$ref")
                if injury_url:
                    injury_data = requests.get(injury_url, timeout=10).json()
                    injuries.append(self._parse_injury(injury_data))

            return injuries
        except Exception as e:
            print(f"Error fetching injuries for team {team_id}: {e}")
            return []

    def _parse_injury(self, injury_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse injury data from ESPN API"""
        details = injury_data.get("details", {})
        athlete_ref = injury_data.get("athlete", {}).get("$ref", "")
        athlete_id = athlete_ref.split("/")[-1].split("?")[0] if athlete_ref else None

        return {
            "injury_id": injury_data.get("id"),
            "athlete_id": athlete_id,
            "status": injury_data.get("status"),
            "injury_type": details.get("type"),
            "location": details.get("location"),
            "detail": details.get("detail"),
            "side": details.get("side"),
            "return_date": details.get("returnDate"),
            "short_comment": injury_data.get("shortComment"),
            "long_comment": injury_data.get("longComment"),
            "date": injury_data.get("date"),
        }

    def _store_injuries(
        self, sport: str, team_id: str, team_name: str, injuries: List[Dict[str, Any]]
    ):
        """Store injury data in DynamoDB"""
        timestamp = datetime.now(timezone.utc).isoformat()

        item = {
            "pk": f"INJURIES#{sport}#{team_id}",
            "sk": f"REPORT#{timestamp}",
            "sport": sport,
            "team_id": team_id,
            "team_name": team_name,
            "injuries": injuries,
            "injury_count": len(injuries),
            "collected_at": timestamp,
        }

        self.table.put_item(Item=item)


def lambda_handler(event, context):
    """Lambda handler for injury collection"""
    collector = InjuryCollector()
    sport = event.get("sport", "basketball_nba")

    injuries_collected = collector.collect_injuries_for_sport(sport)

    return {
        "statusCode": 200,
        "body": {
            "message": f"Collected {injuries_collected} injuries for {sport}",
            "sport": sport,
            "injuries_collected": injuries_collected,
        },
    }
