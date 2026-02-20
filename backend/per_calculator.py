"""
Calculate Player Efficiency Rating (PER) for NBA players
Based on Basketball-Reference formula
"""
import os
import boto3
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from decimal import Decimal
import requests

class PERCalculator:
    def __init__(self):
        self.table = boto3.resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
        self.espn_base_url = "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba"
    
    def calculate_player_per(self, player_stats: Dict) -> float:
        """Calculate PER from player box score stats"""
        # Extract stats
        mp = float(player_stats.get('minutes', 0))
        if mp == 0:
            return 0.0
        
        pts = float(player_stats.get('points', 0))
        fgm = float(player_stats.get('fieldGoalsMade', 0))
        fga = float(player_stats.get('fieldGoalsAttempted', 0))
        ftm = float(player_stats.get('freeThrowsMade', 0))
        fta = float(player_stats.get('freeThrowsAttempted', 0))
        threes = float(player_stats.get('threePointFieldGoalsMade', 0))
        ast = float(player_stats.get('assists', 0))
        reb = float(player_stats.get('rebounds', 0))
        orb = float(player_stats.get('offensiveRebounds', 0))
        drb = float(player_stats.get('defensiveRebounds', 0))
        stl = float(player_stats.get('steals', 0))
        blk = float(player_stats.get('blocks', 0))
        tov = float(player_stats.get('turnovers', 0))
        pf = float(player_stats.get('fouls', 0))
        
        # Simplified PER calculation (without league averages)
        # Positive contributions
        positive = (
            pts +
            reb * 1.2 +
            ast * 1.5 +
            stl * 2.0 +
            blk * 2.0 +
            threes * 0.5
        )
        
        # Negative contributions
        negative = (
            (fga - fgm) * 0.5 +
            (fta - ftm) * 0.5 +
            tov * 2.0 +
            pf * 0.5
        )
        
        # Per-minute rating
        per = ((positive - negative) / mp) * 10
        
        return round(max(0, per), 2)
    
    def get_player_recent_games(self, player_name: str, days_back: int = 30) -> List[Dict]:
        """Get recent games for a player from DynamoDB"""
        cutoff_date = (datetime.utcnow() - timedelta(days=days_back)).isoformat()
        
        # Query player stats from team stats records
        response = self.table.query(
            IndexName="GenericQueryIndex",
            KeyConditionExpression="gsi_pk = :pk AND gsi_sk > :cutoff",
            ExpressionAttributeValues={
                ":pk": "PLAYER_STATS#basketball_nba",
                ":cutoff": cutoff_date
            },
            ScanIndexForward=False,
            Limit=50
        )
        
        # Filter for specific player
        player_games = []
        for item in response.get("Items", []):
            if item.get("player_name", "").lower() == player_name.lower():
                player_games.append(item)
        
        return player_games
    
    def calculate_rolling_per(self, player_name: str, games: int = 10) -> Optional[Dict]:
        """Calculate rolling average PER for a player"""
        recent_games = self.get_player_recent_games(player_name)
        
        if not recent_games:
            return None
        
        # Calculate PER for each game
        per_values = []
        for game in recent_games[:games]:
            stats = game.get("stats", {})
            per = self.calculate_player_per(stats)
            if per > 0:
                per_values.append(per)
        
        if not per_values:
            return None
        
        avg_per = sum(per_values) / len(per_values)
        
        return {
            "player_name": player_name,
            "avg_per": round(avg_per, 2),
            "games_analyzed": len(per_values),
            "recent_per_values": per_values[:5],
            "calculated_at": datetime.utcnow().isoformat()
        }
    
    def store_player_per(self, player_name: str, per_data: Dict):
        """Store player PER in DynamoDB"""
        normalized_name = player_name.strip().replace(" ", "_").upper()
        timestamp = datetime.utcnow().isoformat()
        
        # Clear old latest flag
        response = self.table.query(
            KeyConditionExpression="pk = :pk",
            FilterExpression="latest = :true",
            ExpressionAttributeValues={
                ":pk": f"PER#basketball_nba#{normalized_name}",
                ":true": True
            }
        )
        
        for item in response.get("Items", []):
            self.table.update_item(
                Key={"pk": item["pk"], "sk": item["sk"]},
                UpdateExpression="REMOVE latest"
            )
        
        # Store new PER
        self.table.put_item(Item={
            "pk": f"PER#basketball_nba#{normalized_name}",
            "sk": timestamp,
            "gsi_pk": "PER#basketball_nba",
            "gsi_sk": timestamp,
            "player_name": player_name,
            "avg_per": Decimal(str(per_data["avg_per"])),
            "games_analyzed": per_data["games_analyzed"],
            "recent_per_values": [Decimal(str(v)) for v in per_data["recent_per_values"]],
            "calculated_at": timestamp,
            "latest": True
        })
    
    def get_player_per(self, player_name: str) -> Optional[float]:
        """Get latest PER for a player"""
        normalized_name = player_name.strip().replace(" ", "_").upper()
        
        response = self.table.query(
            KeyConditionExpression="pk = :pk",
            FilterExpression="latest = :true",
            ExpressionAttributeValues={
                ":pk": f"PER#basketball_nba#{normalized_name}",
                ":true": True
            },
            Limit=1
        )
        
        items = response.get("Items", [])
        if items:
            return float(items[0].get("avg_per", 0))
        return None
