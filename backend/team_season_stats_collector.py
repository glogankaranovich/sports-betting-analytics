"""
Team Season Stats Collector - Fetches season-level statistics from ESPN API
Uses /teams/:team/statistics endpoint for accurate season averages
"""

import os
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

import boto3
import requests


class TeamSeasonStatsCollector:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table(os.getenv("DYNAMODB_TABLE"))
        self.espn_base_url = "http://site.api.espn.com/apis/site/v2/sports"

    def collect_team_stats(self, sport: str, team_abbr: str) -> Optional[Dict]:
        """Collect season statistics for a team"""
        sport_map = {
            "basketball_nba": "basketball/nba",
            "americanfootball_nfl": "football/nfl",
            "baseball_mlb": "baseball/mlb",
            "icehockey_nhl": "hockey/nhl",
        }
        
        espn_sport = sport_map.get(sport)
        if not espn_sport:
            return None
        
        url = f"{self.espn_base_url}/{espn_sport}/teams/{team_abbr}/statistics"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") != "success":
                return None
            
            # Parse stats based on sport
            if sport == "basketball_nba":
                return self._parse_nba_stats(data)
            elif sport == "americanfootball_nfl":
                return self._parse_nfl_stats(data)
            elif sport == "icehockey_nhl":
                return self._parse_nhl_stats(data)
            elif sport == "baseball_mlb":
                return self._parse_mlb_stats(data)
            
            return None
            
        except Exception as e:
            print(f"Error fetching stats for {team_abbr}: {e}")
            return None

    def _parse_nba_stats(self, data: Dict) -> Dict:
        """Parse NBA statistics"""
        stats = {}
        categories = data.get("results", {}).get("stats", {}).get("categories", [])
        
        for category in categories:
            for stat in category.get("stats", []):
                name = stat.get("name")
                value = stat.get("value")
                
                if name == "avgPoints":
                    stats["adjusted_ppg"] = value
                elif name == "fieldGoalPct":
                    stats["fg_pct"] = value
                elif name == "threePointPct":
                    stats["three_pt_pct"] = value
                elif name == "avgRebounds":
                    stats["rebounds_per_game"] = value
                elif name == "avgAssists":
                    stats["assists_per_game"] = value
                elif name == "avgTurnovers":
                    stats["turnovers_per_game"] = value
                elif name == "avgFieldGoalsAttempted":
                    stats["fga_per_game"] = value
                elif name == "avgOffensiveRebounds":
                    stats["offensive_rebounds"] = value
                elif name == "avgFreeThrowsAttempted":
                    stats["fta_per_game"] = value
        
        # Calculate pace (possessions per game)
        # Pace = FGA - ORB + TO + 0.4*FTA
        if all(k in stats for k in ["fga_per_game", "offensive_rebounds", "turnovers_per_game", "fta_per_game"]):
            stats["pace"] = (stats["fga_per_game"] - stats["offensive_rebounds"] + 
                           stats["turnovers_per_game"] + 0.4 * stats["fta_per_game"])
        
        # Calculate offensive efficiency (points per 100 possessions)
        if "adjusted_ppg" in stats and "pace" in stats and stats["pace"] > 0:
            stats["offensive_efficiency"] = (stats["adjusted_ppg"] / stats["pace"]) * 100
        
        return stats

    def _parse_nfl_stats(self, data: Dict) -> Dict:
        """Parse NFL statistics"""
        stats = {}
        categories = data.get("results", {}).get("stats", {}).get("categories", [])
        
        for category in categories:
            cat_name = category.get("name")
            for stat in category.get("stats", []):
                name = stat.get("name")
                value = stat.get("value")
                per_game = stat.get("perGameValue", value)
                
                if cat_name == "passing":
                    if name == "yardsPerGame":
                        stats["pass_yards_per_game"] = value
                    elif name == "passerRating":
                        stats["pass_efficiency"] = value
                elif cat_name == "rushing":
                    if name == "yardsPerGame":
                        stats["rush_yards_per_game"] = value
                elif cat_name == "miscellaneous":
                    if name == "totalYardsPerGame":
                        stats["adjusted_total_yards"] = value
                    elif name == "turnovers":
                        stats["turnovers"] = value
                    elif name == "thirdDownConvPct":
                        stats["third_down_pct"] = value
        
        # Calculate turnover differential (negative = bad for offense)
        if "turnovers" in stats:
            stats["turnover_differential"] = -stats["turnovers"]
        
        return stats

    def _parse_nhl_stats(self, data: Dict) -> Dict:
        """Parse NHL statistics"""
        stats = {}
        categories = data.get("results", {}).get("stats", {}).get("categories", [])
        
        for category in categories:
            for stat in category.get("stats", []):
                name = stat.get("name")
                value = stat.get("value")
                
                if name == "avgGoals":
                    stats["goals_per_game"] = value
                elif name == "avgShots":
                    stats["shots_per_game"] = value
                elif name == "powerPlayPct":
                    stats["power_play_pct"] = value
                elif name == "penaltyKillPct":
                    stats["penalty_kill_pct"] = value
                elif name == "avgShotsAgainst":
                    stats["shots_against_per_game"] = value
        
        return stats

    def _parse_mlb_stats(self, data: Dict) -> Dict:
        """Parse MLB statistics"""
        stats = {}
        categories = data.get("results", {}).get("stats", {}).get("categories", [])
        
        for category in categories:
            cat_name = category.get("name")
            for stat in category.get("stats", []):
                name = stat.get("name")
                value = stat.get("value")
                
                if cat_name == "batting" and name == "OPS":
                    stats["ops"] = value
                elif cat_name == "batting" and name == "avg":
                    stats["batting_avg"] = value
                elif cat_name == "pitching" and name == "ERA":
                    stats["era"] = value
                elif cat_name == "pitching" and name == "WHIP":
                    stats["whip"] = value
        
        return stats

    def store_team_stats(self, sport: str, team_name: str, team_abbr: str, stats: Dict):
        """Store team season stats in DynamoDB"""
        try:
            normalized_name = team_name.lower().replace(" ", "_")
            pk = f"ADJUSTED_METRICS#{sport}#{normalized_name}"  # Match what models expect
            sk = datetime.utcnow().isoformat()
            
            stats_decimal = self._convert_to_decimal(stats)
            
            self.table.put_item(
                Item={
                    "pk": pk,
                    "sk": sk,
                    "sport": sport,
                    "team_name": team_name,
                    "team_abbr": team_abbr,
                    "metrics": stats_decimal,
                    "latest": True,
                    "updated_at": sk,
                }
            )
            
            print(f"Stored season stats for {team_name}")
            
        except Exception as e:
            print(f"Error storing stats for {team_name}: {e}")

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
    """Lambda handler for collecting team season stats"""
    collector = TeamSeasonStatsCollector()
    
    # Example: collect stats for specific teams
    # In production, would iterate through all teams
    teams = {
        "basketball_nba": [("Los Angeles Lakers", "lal"), ("Boston Celtics", "bos")],
        "americanfootball_nfl": [("Buffalo Bills", "buf"), ("Kansas City Chiefs", "kc")],
        "icehockey_nhl": [("Boston Bruins", "bos"), ("Toronto Maple Leafs", "tor")],
        "baseball_mlb": [("Boston Red Sox", "bos"), ("New York Yankees", "nyy")],
    }
    
    total_collected = 0
    
    for sport, team_list in teams.items():
        for team_name, team_abbr in team_list:
            stats = collector.collect_team_stats(sport, team_abbr)
            if stats:
                collector.store_team_stats(sport, team_name, team_abbr, stats)
                total_collected += 1
    
    return {
        "statusCode": 200,
        "body": f"Collected stats for {total_collected} teams"
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    lambda_handler({}, {})
