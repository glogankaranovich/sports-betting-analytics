"""Fundamentals Model - Core team statistics and efficiency metrics"""

import logging
import os
from typing import Dict, List, Optional

import boto3

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class FundamentalsModel(BaseModel):
    """
    Fundamentals-based model using opponent-adjusted metrics, Elo, weather, and fatigue.
    
    Strategy:
    - Uses Elo ratings for team strength
    - Analyzes opponent-adjusted efficiency metrics
    - Factors in travel fatigue and rest
    - Considers weather impact for outdoor sports
    - Evaluates pace/tempo advantages
    
    Supported Sports:
    - NBA, NHL, NFL (full metrics)
    - EPL, MLS (soccer metrics)
    - NCAAF, NCAAB, WNCAAB, WNBA (college/women's metrics)
    - MLB (Elo/fatigue only, emits metric for missing stats)
    """
    
    def __init__(self, dynamodb_table=None):
        super().__init__()
        self.table = dynamodb_table
        if not self.table:
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)
        
        from elo_calculator import EloCalculator
        from travel_fatigue_calculator import TravelFatigueCalculator
        
        self.elo_calculator = EloCalculator()
        self.fatigue_calculator = TravelFatigueCalculator()
    
    def analyze_game_odds(self, game_id: str, odds_items: List[Dict], game_info: Dict):
        """Analyze game using fundamental team strength metrics"""
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        game_date = game_info.get("commence_time")
        
        home_elo = self.elo_calculator.get_team_rating(sport, home_team)
        away_elo = self.elo_calculator.get_team_rating(sport, away_team)
        elo_diff = home_elo - away_elo
        
        home_metrics = self._get_adjusted_metrics(sport, home_team)
        away_metrics = self._get_adjusted_metrics(sport, away_team)
        
        home_fatigue = self.fatigue_calculator.calculate_fatigue_score(home_team, sport, game_date)
        away_fatigue = self.fatigue_calculator.calculate_fatigue_score(away_team, sport, game_date)
        
        weather_impact = 0
        weather_context = ""
        if sport in ['americanfootball_nfl', 'baseball_mlb', 'soccer_epl', 'soccer_usa_mls', 'americanfootball_ncaaf']:
            try:
                weather_response = self.table.get_item(Key={"pk": f"WEATHER#{game_id}", "sk": "latest"})
                weather_data = weather_response.get("Item")
                if weather_data:
                    impact = weather_data.get("impact", "low")
                    if impact == "high":
                        weather_impact = -5
                        weather_context = " High weather impact."
                    elif impact == "moderate":
                        weather_impact = -2
                        weather_context = " Moderate weather impact."
            except:
                pass
        
        home_score = 50
        home_score += min(max(elo_diff / 10, -20), 20)
        
        metrics_diff = 0
        pace_diff = 0
        if home_metrics and away_metrics:
            metrics_diff = self._compare_metrics(home_metrics, away_metrics, sport)
            home_score += min(max(metrics_diff, -15), 15)
            pace_diff = self._calculate_pace_advantage(home_metrics, away_metrics, sport)
            home_score += min(max(pace_diff, -5), 5)
        
        fatigue_diff = away_fatigue['fatigue_score'] - home_fatigue['fatigue_score']
        home_score += min(max(fatigue_diff / 10, -10), 10)
        home_score += 5
        home_score += weather_impact
        
        confidence = abs(home_score - 50) / 50 * 0.4 + 0.5
        confidence = min(max(confidence, 0.5), 0.85)
        pick = home_team if home_score > 50 else away_team
        
        reasons = []
        if abs(elo_diff) > 50:
            reasons.append(f"Elo: {home_team} {home_elo:.0f} vs {away_team} {away_elo:.0f}")
        if home_metrics and away_metrics:
            reasons.append(f"Efficiency metrics favor {home_team if metrics_diff > 0 else away_team}")
            if abs(pace_diff) > 2:
                reasons.append(f"Pace advantage: {home_team if pace_diff > 0 else away_team}")
        if abs(fatigue_diff) > 20:
            reasons.append(f"Fatigue advantage: {home_team if fatigue_diff > 0 else away_team}")
        
        reasoning = "Fundamentals: " + ", ".join(reasons) if reasons else f"Slight edge to {pick}"
        reasoning += weather_context
        confidence = self._adjust_confidence(confidence, "fundamentals", sport)
        
        return AnalysisResult(
            game_id=game_id,
            model="fundamentals",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_date,
            prediction=pick,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110
        )
    
    def analyze_prop_odds(self, prop_item: Dict):
        return None
    
    def _get_adjusted_metrics(self, sport: str, team_name: str) -> Optional[Dict]:
        try:
            normalized_name = team_name.strip().replace(" ", "_").upper()
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                FilterExpression="latest = :true",
                ExpressionAttributeValues={
                    ":pk": f"ADJUSTED_METRICS#{sport}#{normalized_name}",
                    ":true": True
                },
                Limit=1
            )
            items = response.get("Items", [])
            return items[0].get("metrics") if items else None
        except:
            return None
    
    def _calculate_pace_advantage(self, home_metrics: Dict, away_metrics: Dict, sport: str) -> float:
        try:
            if sport in ["basketball_nba", "basketball_ncaab", "basketball_wncaab", "basketball_wnba"]:
                home_pace = float(home_metrics.get("pace", 100))
                away_pace = float(away_metrics.get("pace", 100))
                home_off_eff = float(home_metrics.get("offensive_efficiency", 110))
                away_def_eff = float(away_metrics.get("defensive_efficiency", 110))
                
                pace_diff = home_pace - away_pace
                eff_diff = home_off_eff - away_def_eff
                
                if pace_diff > 0 and eff_diff > 0:
                    return min(pace_diff / 2, 5)
                elif pace_diff < 0 and eff_diff < 0:
                    return max(pace_diff / 2, -5)
                return 0
            elif sport == "icehockey_nhl":
                home_shots = float(home_metrics.get("shots_per_game", 30))
                away_shots = float(away_metrics.get("shots_per_game", 30))
                return (home_shots - away_shots) / 5
            return 0
        except:
            return 0
    
    def _compare_metrics(self, home_metrics: Dict, away_metrics: Dict, sport: str) -> float:
        try:
            if sport in ["basketball_nba", "basketball_ncaab", "basketball_wncaab", "basketball_wnba"]:
                home_ppg = float(home_metrics.get("adjusted_ppg", 0))
                away_ppg = float(away_metrics.get("adjusted_ppg", 0))
                home_fg = float(home_metrics.get("fg_pct", 0))
                away_fg = float(away_metrics.get("fg_pct", 0))
                home_off_eff = float(home_metrics.get("offensive_efficiency", 110))
                away_def_eff = float(away_metrics.get("defensive_efficiency", 110))
                
                ppg_diff = (home_ppg - away_ppg) / 5
                fg_diff = (home_fg - away_fg) * 20
                eff_diff = (home_off_eff - away_def_eff) / 5
                return (ppg_diff + fg_diff + eff_diff) / 3
            
            elif sport in ["americanfootball_nfl", "americanfootball_ncaaf"]:
                home_yards = float(home_metrics.get("adjusted_total_yards", 0))
                away_yards = float(away_metrics.get("adjusted_total_yards", 0))
                home_pass_eff = float(home_metrics.get("pass_efficiency", 100))
                away_pass_eff = float(away_metrics.get("pass_efficiency", 100))
                home_turnover = float(home_metrics.get("turnover_differential", 0))
                away_turnover = float(away_metrics.get("turnover_differential", 0))
                
                yards_diff = (home_yards - away_yards) / 50
                pass_diff = (home_pass_eff - away_pass_eff) / 20
                turnover_diff = (home_turnover - away_turnover) / 2
                return (yards_diff + pass_diff + turnover_diff) / 3
            
            elif sport == "icehockey_nhl":
                home_shots = float(home_metrics.get("shots_per_game", 30))
                away_shots = float(away_metrics.get("shots_per_game", 30))
                home_pp = float(home_metrics.get("power_play_pct", 20))
                away_pp = float(away_metrics.get("power_play_pct", 20))
                
                shots_diff = (home_shots - away_shots) / 5
                pp_diff = (home_pp - away_pp) / 5
                return (shots_diff + pp_diff) / 2
            
            elif sport in ["soccer_epl", "soccer_usa_mls"]:
                home_shots = float(home_metrics.get("shots_on_goal", 5))
                away_shots = float(away_metrics.get("shots_on_goal", 5))
                home_poss = float(home_metrics.get("possession", 50))
                away_poss = float(away_metrics.get("possession", 50))
                
                shots_diff = (home_shots - away_shots) / 3
                poss_diff = (home_poss - away_poss) / 10
                return (shots_diff + poss_diff) / 2
            
            elif sport == "baseball_mlb":
                self._emit_unsupported_sport_metric(sport)
                return 0.0
            
            self._emit_unsupported_sport_metric(sport)
            return 0.0
        except Exception as e:
            logger.error(f"Error comparing metrics: {e}")
            return 0.0
    
    def _emit_unsupported_sport_metric(self, sport: str):
        try:
            cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")
            cloudwatch.put_metric_data(
                Namespace="SportsAnalytics/Models",
                MetricData=[{
                    "MetricName": "UnsupportedSportPrediction",
                    "Value": 1,
                    "Unit": "Count",
                    "Dimensions": [
                        {"Name": "Model", "Value": "fundamentals"},
                        {"Name": "Sport", "Value": sport}
                    ]
                }]
            )
            logger.warning(f"Fundamentals model does not fully support {sport} - missing team stats")
        except Exception as e:
            logger.error(f"Error emitting metric: {e}")
