"""Matchup Model - Head-to-head history and style matchups"""

import logging
from typing import Dict, List, Optional

from ml.models.base import BaseModel
from ml.types import AnalysisResult
from weather_collector import WeatherCollector

logger = logging.getLogger(__name__)


class MatchupModel(BaseModel):
    """Model that analyzes head-to-head history and style matchups with weather"""

    def __init__(self, dynamodb_table=None):
        import os
        import boto3

        self.table = dynamodb_table
        if not self.table:
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)
        
        self.weather_collector = WeatherCollector()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")

        h2h_advantage = self._get_h2h_advantage(sport, home_team, away_team)
        style_advantage = self._get_style_matchup(sport, home_team, away_team)
        total_advantage = (h2h_advantage * 0.6) + (style_advantage * 0.4)

        confidence = 0.5 + (abs(total_advantage) * 0.1)
        confidence = max(0.3, min(0.85, confidence))
        
        weather_context = ""
        try:
            if sport in ['americanfootball_nfl', 'baseball_mlb', 'soccer_epl']:
                weather_response = self.table.get_item(
                    Key={"pk": f"WEATHER#{game_id}", "sk": "latest"}
                )
                weather_data = weather_response.get("Item")
                
                if weather_data and weather_data.get("impact") in ["high", "moderate"]:
                    impact = weather_data.get("impact")
                    wind = weather_data.get("wind_mph", 0)
                    temp = weather_data.get("temp_f", 70)
                    precip = weather_data.get("precip_in", 0)
                    
                    conditions = []
                    if wind > 15:
                        conditions.append(f"{wind}mph wind")
                    if temp < 32:
                        conditions.append(f"{temp}°F")
                    if precip > 0.2:
                        conditions.append(f"{precip}\" rain")
                    
                    if conditions:
                        weather_context = f" Weather impact ({impact}): {', '.join(conditions)}."
                        confidence = max(confidence - 0.05, 0.3)
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")

        pick = home_team if total_advantage > 0 else away_team
        favored_team = home_team if total_advantage > 0 else away_team
        
        reasons = []
        if abs(h2h_advantage) > 0.5:
            reasons.append(f"head-to-head record favors {home_team if h2h_advantage > 0 else away_team}")
        
        if abs(style_advantage) > 0.5:
            reasons.append(f"offensive/defensive matchup favors {home_team if style_advantage > 0 else away_team}")
        
        reasoning = ", ".join(reasons).capitalize() + f".{weather_context}" if reasons else f"Slight edge to {favored_team}.{weather_context}"

        return AnalysisResult(
            game_id=game_id,
            model="matchup",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=pick,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        try:
            player = prop_item.get("player_name")
            if not player:
                return None

            sport = prop_item.get("sport")
            game_id = prop_item.get("event_id")
            game_response = self.table.get_item(
                Key={"pk": f"GAME#{game_id}", "sk": "LATEST"}
            )
            game_item = game_response.get("Item", {})
            home_team = game_item.get("home_team", "")
            away_team = game_item.get("away_team", "")

            player_team = prop_item.get("team", "")
            opponent = away_team if player_team == home_team else home_team

            vs_opponent_avg = self._get_player_vs_opponent_avg(
                sport, player, opponent, prop_item.get("market_key")
            )

            if vs_opponent_avg is None:
                return None

            prop_line = float(prop_item.get("point", 0))
            diff = vs_opponent_avg - prop_line
            confidence = 0.5 + min(abs(diff) * 0.05, 0.25)

            if diff > 2:
                prediction = f"Over {prop_line}"
                reasoning = f"Averages {vs_opponent_avg:.1f} vs {opponent}"
            elif diff < -2:
                prediction = f"Under {prop_line}"
                reasoning = f"Averages {vs_opponent_avg:.1f} vs {opponent}"
            else:
                return None

            return AnalysisResult(
                game_id=game_id,
                model="matchup",
                analysis_type="prop",
                sport=sport,
                home_team=home_team,
                away_team=away_team,
                commence_time=prop_item.get("commence_time"),
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
                recommended_odds=-110,
            )
        except Exception as e:
            logger.error(f"Error analyzing prop matchup: {e}", exc_info=True)
            return None

    def _get_h2h_advantage(self, sport: str, home_team: str, away_team: str) -> float:
        try:
            home_normalized = home_team.lower().replace(" ", "_")
            away_normalized = away_team.lower().replace(" ", "_")
            teams_sorted = sorted([home_normalized, away_normalized])
            h2h_pk = f"H2H#{sport}#{teams_sorted[0]}#{teams_sorted[1]}"

            response = self.table.query(
                IndexName="H2HIndex",
                KeyConditionExpression="h2h_pk = :pk",
                ExpressionAttributeValues={":pk": h2h_pk},
                ScanIndexForward=False,
                Limit=10,
            )

            home_wins = sum(1 for item in response.get("Items", []) if item.get("winner") == home_team)
            away_wins = sum(1 for item in response.get("Items", []) if item.get("winner") == away_team)
            total_games = home_wins + away_wins

            if total_games == 0:
                return 0.0

            win_rate = home_wins / total_games
            return (win_rate - 0.5) * 4

        except Exception as e:
            logger.error(f"Error getting H2H advantage: {e}", exc_info=True)
            return 0.0

    def _get_style_matchup(self, sport: str, home_team: str, away_team: str) -> float:
        try:
            home_stats = self._get_team_stats(sport, home_team)
            away_stats = self._get_team_stats(sport, away_team)

            if not home_stats or not away_stats:
                return 0.0

            stats_map = {
                "icehockey_nhl": ("Shots", "Power Play Percentage"),
                "basketball_nba": ("Field Goal %", "Defensive Rebounds"),
                "basketball_wnba": ("Field Goal %", "Defensive Rebounds"),
                "americanfootball_nfl": ("Total Yards", "Turnovers"),
                "baseball_mlb": ("Batting Average", "ERA"),
                "soccer_epl": ("ON GOAL", "Effective Tackles"),
                "soccer_usa_mls": ("ON GOAL", "Effective Tackles"),
                "basketball_ncaab": ("Field Goal %", "Defensive Rebounds"),
                "basketball_wncaab": ("Field Goal %", "Defensive Rebounds"),
                "americanfootball_ncaaf": ("Total Yards", "Turnovers"),
            }
            
            if sport not in stats_map:
                return 0.0
                
            offense_stat, defense_stat = stats_map[sport]
            
            home_offense = float(home_stats.get("stats", {}).get(offense_stat, "0"))
            away_offense = float(away_stats.get("stats", {}).get(offense_stat, "0"))
            home_defense = float(home_stats.get("stats", {}).get(defense_stat, "0"))
            away_defense = float(away_stats.get("stats", {}).get(defense_stat, "0"))
            
            if sport == "icehockey_nhl":
                offense_matchup = (home_offense - away_offense) / 10
                defense_matchup = (home_defense - away_defense) / 10
            elif sport in ["basketball_nba", "basketball_wnba", "basketball_ncaab", "basketball_wncaab"]:
                offense_matchup = (home_offense - away_offense) / 10
                defense_matchup = (home_defense - away_defense) / 5
            elif sport in ["americanfootball_nfl", "americanfootball_ncaaf"]:
                offense_matchup = (home_offense - away_offense) / 100
                defense_matchup = (away_defense - home_defense)
            elif sport == "baseball_mlb":
                offense_matchup = (home_offense - away_offense) * 10
                defense_matchup = (away_defense - home_defense) / 2
            elif sport in ["soccer_epl", "soccer_usa_mls"]:
                offense_matchup = (home_offense - away_offense) / 5
                defense_matchup = (home_defense - away_defense) / 10
            else:
                return 0.0
            
            return (offense_matchup + defense_matchup) / 2

        except Exception as e:
            logger.error(f"Error getting style matchup: {e}", exc_info=True)
            return 0.0

    def _get_team_stats(self, sport: str, team: str) -> Optional[Dict]:
        try:
            team_key = team.lower().replace(" ", "_")
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": f"TEAM_STATS#{sport}#{team_key}"},
                ScanIndexForward=False,
                Limit=1,
            )

            items = response.get("Items", [])
            return items[0] if items else None

        except Exception as e:
            logger.error(f"Error getting team stats: {e}", exc_info=True)
            return None

    def _get_player_vs_opponent_avg(
        self, sport: str, player_name: str, opponent: str, stat_key: str
    ) -> Optional[float]:
        try:
            normalized_player = player_name.lower().replace(" ", "_")
            normalized_opponent = opponent.lower().replace(" ", "_")

            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={
                    ":pk": f"PLAYER_STATS#{sport}#{normalized_player}",
                },
                ScanIndexForward=False,
                Limit=20,
            )

            items = response.get("Items", [])
            if not items:
                return None

            opponent_games = [
                item
                for item in items
                if normalized_opponent in item.get("sk", "").lower()
            ][:5]

            if not opponent_games:
                return None

            stat_map = {
                "player_points": "PTS",
                "player_rebounds": "REB",
                "player_assists": "AST",
                "player_threes": "3PM",
            }
            stat_name = stat_map.get(stat_key, "PTS")

            total = 0
            count = 0
            for item in opponent_games:
                stats = item.get("stats", {})
                stat_value = stats.get(stat_name)
                if stat_value:
                    total += float(stat_value)
                    count += 1

            return total / count if count > 0 else None

        except Exception as e:
            logger.error(f"Error getting player vs opponent avg: {e}", exc_info=True)
            return None
