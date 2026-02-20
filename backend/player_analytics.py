"""
Enhanced player analytics: usage rate, home/away splits, matchup history
"""
import os
import boto3
from typing import Dict, List, Optional
from datetime import datetime, timedelta

class PlayerAnalytics:
    def __init__(self):
        self.table = boto3.resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
    
    def calculate_usage_rate(self, player_stats: List[Dict], team_stats: Dict) -> float:
        """
        Calculate player usage rate (simplified)
        Usage = (Player FGA + 0.44 * Player FTA + Player TOV) / (Team FGA + 0.44 * Team FTA + Team TOV)
        """
        try:
            if not player_stats or not team_stats:
                return 0.0
            
            # Average player stats
            player_fga = sum(float(s.get('stats', {}).get('fieldGoalsAttempted', 0)) for s in player_stats) / len(player_stats)
            player_fta = sum(float(s.get('stats', {}).get('freeThrowsAttempted', 0)) for s in player_stats) / len(player_stats)
            player_tov = sum(float(s.get('stats', {}).get('turnovers', 0)) for s in player_stats) / len(player_stats)
            
            # Team averages
            team_fga = float(team_stats.get('fga', 85))
            team_fta = float(team_stats.get('fta', 25))
            team_tov = float(team_stats.get('tov', 15))
            
            player_possessions = player_fga + 0.44 * player_fta + player_tov
            team_possessions = team_fga + 0.44 * team_fta + team_tov
            
            if team_possessions == 0:
                return 0.0
            
            usage_rate = (player_possessions / team_possessions) * 100
            return round(usage_rate, 2)
        except:
            return 0.0
    
    def get_home_away_splits(self, player_name: str, sport: str, games: int = 20) -> Dict:
        """Calculate player's home vs away performance splits"""
        try:
            normalized_name = player_name.lower().replace(" ", "_")
            pk = f"PLAYER_STATS#{sport}#{normalized_name}"
            
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                Limit=games,
                ScanIndexForward=False
            )
            
            items = response.get("Items", [])
            
            home_stats = []
            away_stats = []
            
            for item in items:
                stats = item.get("stats", {})
                is_home = item.get("is_home", True)
                
                if is_home:
                    home_stats.append(stats)
                else:
                    away_stats.append(stats)
            
            # Calculate averages for key stats
            home_avg = self._calculate_avg_stats(home_stats, sport)
            away_avg = self._calculate_avg_stats(away_stats, sport)
            
            return {
                "home": home_avg,
                "away": away_avg,
                "home_games": len(home_stats),
                "away_games": len(away_stats),
                "split_difference": self._calculate_split_diff(home_avg, away_avg, sport)
            }
        except Exception as e:
            print(f"Error calculating splits: {e}")
            return {}
    
    def get_matchup_history(self, player_name: str, opponent: str, sport: str) -> Dict:
        """Get player's historical performance vs specific opponent"""
        try:
            normalized_name = player_name.lower().replace(" ", "_")
            normalized_opponent = opponent.lower().replace(" ", "_")
            pk = f"PLAYER_STATS#{sport}#{normalized_name}"
            
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                ScanIndexForward=False,
                Limit=50
            )
            
            items = response.get("Items", [])
            
            # Filter for games vs this opponent
            matchup_games = [
                item for item in items 
                if normalized_opponent in item.get("sk", "").lower()
            ]
            
            if not matchup_games:
                return {"games": 0, "avg_stats": {}}
            
            stats_list = [game.get("stats", {}) for game in matchup_games]
            avg_stats = self._calculate_avg_stats(stats_list, sport)
            
            return {
                "games": len(matchup_games),
                "avg_stats": avg_stats,
                "last_game": matchup_games[0].get("stats", {}) if matchup_games else {}
            }
        except Exception as e:
            print(f"Error getting matchup history: {e}")
            return {"games": 0, "avg_stats": {}}
    
    def get_recent_form_trend(self, player_name: str, sport: str, games: int = 10) -> Dict:
        """Calculate if player is trending up or down"""
        try:
            normalized_name = player_name.lower().replace(" ", "_")
            pk = f"PLAYER_STATS#{sport}#{normalized_name}"
            
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                Limit=games,
                ScanIndexForward=False
            )
            
            items = response.get("Items", [])
            
            if len(items) < 5:
                return {"trend": "insufficient_data", "direction": 0}
            
            # Split into recent half and older half
            mid = len(items) // 2
            recent_games = items[:mid]
            older_games = items[mid:]
            
            recent_avg = self._calculate_avg_stats([g.get("stats", {}) for g in recent_games], sport)
            older_avg = self._calculate_avg_stats([g.get("stats", {}) for g in older_games], sport)
            
            # Compare key stat (points for most sports)
            key_stat = self._get_key_stat(sport)
            recent_val = recent_avg.get(key_stat, 0)
            older_val = older_avg.get(key_stat, 0)
            
            if older_val == 0:
                return {"trend": "stable", "direction": 0}
            
            pct_change = ((recent_val - older_val) / older_val) * 100
            
            if pct_change > 10:
                trend = "improving"
                direction = 1
            elif pct_change < -10:
                trend = "declining"
                direction = -1
            else:
                trend = "stable"
                direction = 0
            
            return {
                "trend": trend,
                "direction": direction,
                "pct_change": round(pct_change, 1),
                "recent_avg": recent_val,
                "older_avg": older_val
            }
        except Exception as e:
            print(f"Error calculating trend: {e}")
            return {"trend": "error", "direction": 0}
    
    def _calculate_avg_stats(self, stats_list: List[Dict], sport: str) -> Dict:
        """Calculate average stats from list of game stats"""
        if not stats_list:
            return {}
        
        key_stats = self._get_key_stats(sport)
        avg_stats = {}
        
        for stat in key_stats:
            values = [float(s.get(stat, 0)) for s in stats_list if stat in s]
            if values:
                avg_stats[stat] = round(sum(values) / len(values), 2)
        
        return avg_stats
    
    def _get_key_stats(self, sport: str) -> List[str]:
        """Get key stats to track by sport"""
        if sport == "basketball_nba":
            return ["points", "rebounds", "assists", "fieldGoalsMade", "fieldGoalsAttempted", "per"]
        elif sport == "americanfootball_nfl":
            return ["passingYards", "passingTouchdowns", "rushingYards", "receivingYards", "receptions", "efficiency"]
        else:
            return ["points", "assists"]
    
    def _get_key_stat(self, sport: str) -> str:
        """Get primary stat for trend analysis"""
        if sport == "basketball_nba":
            return "points"
        elif sport == "americanfootball_nfl":
            return "passingYards"
        return "points"
    
    def _calculate_split_diff(self, home_avg: Dict, away_avg: Dict, sport: str) -> float:
        """Calculate percentage difference between home and away performance"""
        key_stat = self._get_key_stat(sport)
        home_val = home_avg.get(key_stat, 0)
        away_val = away_avg.get(key_stat, 0)
        
        if away_val == 0:
            return 0.0
        
        return round(((home_val - away_val) / away_val) * 100, 1)
