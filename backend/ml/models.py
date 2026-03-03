"""
ML Models for Sports Betting Analytics

Error Handling Strategy:
- All models use try/except blocks to catch errors gracefully
- Errors are logged with logger.error() including exception details
- analyze_game_odds() and analyze_prop_odds() return None on error
- Helper methods return safe defaults (0.0, None, empty dict) on error
- This ensures one model's failure doesn't break the entire analysis pipeline
"""

import logging
import math
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

import boto3

from player_analytics import PlayerAnalytics
from elo_calculator import EloCalculator
from travel_fatigue_calculator import TravelFatigueCalculator
from weather_collector import WeatherCollector
from ml.types import AnalysisResult

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class GameAnalysis:
    game_id: str
    sport: str
    home_win_probability: float
    away_win_probability: float
    confidence_score: float
    value_bets: List[str]


@dataclass
class PropAnalysis:
    game_id: str
    sport: str
    player_name: str
    prop_type: str
    line: float
    over_probability: float
    under_probability: float
    confidence_score: float
    value_bets: List[str]




class BaseAnalysisModel:
    """Base class for all analysis models"""

    def __init__(self):
        self.performance_tracker = None
        self.inefficiency_tracker = None
        table_name = os.getenv("DYNAMODB_TABLE")
        if table_name:
            from model_performance import ModelPerformanceTracker
            from market_inefficiency_tracker import MarketInefficiencyTracker
            self.performance_tracker = ModelPerformanceTracker(table_name)
            self.inefficiency_tracker = MarketInefficiencyTracker(table_name)

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """Analyze game odds and return analysis result"""
        raise NotImplementedError("Subclasses must implement analyze_game_odds")

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds and return analysis result"""
        raise NotImplementedError("Subclasses must implement analyze_prop_odds")

    def american_to_decimal(self, american_odds: int) -> float:
        """Convert American odds to decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    def _detect_market_inefficiency(self, model_spread: float, market_spread: float, confidence: float) -> Dict[str, Any]:
        """Detect when model strongly disagrees with market"""
        disagreement = abs(model_spread - market_spread)
        
        # Strong disagreement = model differs by >2 points AND high confidence
        if disagreement > 2.0 and confidence > 0.7:
            return {
                "is_inefficient": True,
                "disagreement": disagreement,
                "edge": "STRONG"
            }
        elif disagreement > 1.0 and confidence > 0.65:
            return {
                "is_inefficient": True,
                "disagreement": disagreement,
                "edge": "MODERATE"
            }
        
        return {"is_inefficient": False, "disagreement": disagreement, "edge": None}

    def _adjust_confidence(self, base_confidence: float, model_name: str, sport: str) -> float:
        """Adjust confidence based on recent model performance"""
        if not self.performance_tracker:
            return base_confidence

        try:
            perf = self.performance_tracker.get_model_performance(model_name, sport, days=30)
            if perf["total_predictions"] < 10:
                return base_confidence
            
            accuracy = perf["accuracy"]
            if accuracy >= 0.60:
                return min(base_confidence + min(0.05, (accuracy - 0.60) * 0.25), 0.95)
            elif accuracy < 0.50:
                return max(base_confidence - (0.50 - accuracy) * 0.5, 0.45)
            return base_confidence
        except Exception as e:
            logger.error(f"Error adjusting confidence: {e}")
            return base_confidence


    def __init__(self, dynamodb_table=None):
        super().__init__()
        self.table = dynamodb_table
        if not self.table:
            import boto3
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)
        
        self.elo_calculator = EloCalculator()
        self.fatigue_calculator = TravelFatigueCalculator()
    
    def analyze_game_odds(self, game_id: str, odds_items: List[Dict], game_info: Dict) -> AnalysisResult:
        """Analyze game using fundamental team strength metrics"""
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        game_date = game_info.get("commence_time")
        
        # Get Elo ratings
        home_elo = self.elo_calculator.get_team_rating(sport, home_team)
        away_elo = self.elo_calculator.get_team_rating(sport, away_team)
        elo_diff = home_elo - away_elo
        
        # Get opponent-adjusted metrics
        home_metrics = self._get_adjusted_metrics(sport, home_team)
        away_metrics = self._get_adjusted_metrics(sport, away_team)
        
        # Get fatigue
        home_fatigue = self.fatigue_calculator.calculate_fatigue_score(home_team, sport, game_date)
        away_fatigue = self.fatigue_calculator.calculate_fatigue_score(away_team, sport, game_date)
        
        # Get weather impact for outdoor sports
        weather_impact = 0
        weather_context = ""
        if sport in ['americanfootball_nfl', 'baseball_mlb', 'soccer_epl']:
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
        
        # Calculate fundamental score (0-100 scale)
        home_score = 50  # Start neutral
        
        # Elo contribution (±20 points max)
        home_score += min(max(elo_diff / 10, -20), 20)
        
        # Adjusted metrics contribution (±15 points max)
        if home_metrics and away_metrics:
            metrics_diff = self._compare_metrics(home_metrics, away_metrics, sport)
            home_score += min(max(metrics_diff, -15), 15)
            
            # Add pace and efficiency factors
            pace_diff = self._calculate_pace_advantage(home_metrics, away_metrics, sport)
            home_score += min(max(pace_diff, -5), 5)
        
        # Fatigue contribution (±10 points max)
        fatigue_diff = away_fatigue['fatigue_score'] - home_fatigue['fatigue_score']
        home_score += min(max(fatigue_diff / 10, -10), 10)
        
        # Home court advantage (+5 points)
        home_score += 5
        
        # Weather impact
        home_score += weather_impact
        
        # Convert to confidence and prediction
        confidence = abs(home_score - 50) / 50 * 0.4 + 0.5  # Scale to 0.5-0.9
        confidence = min(max(confidence, 0.5), 0.85)
        
        pick = home_team if home_score > 50 else away_team
        
        # Build reasoning
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
    
    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Props not supported for fundamentals model"""
        return None
    
    def _get_adjusted_metrics(self, sport: str, team_name: str) -> Optional[Dict]:
        """Get opponent-adjusted metrics for a team"""
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
        """Calculate pace/tempo advantage by sport"""
        try:
            if sport == "basketball_nba":
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
                # Shot volume advantage
                home_shots = float(home_metrics.get("shots_per_game", 30))
                away_shots = float(away_metrics.get("shots_per_game", 30))
                return (home_shots - away_shots) / 5
            
            # NFL, MLB, Soccer don't have meaningful pace metrics from ESPN
            return 0
        except:
            return 0
    
    def _compare_metrics(self, home_metrics: Dict, away_metrics: Dict, sport: str) -> float:
        """Compare adjusted metrics between teams, return difference (-15 to +15)"""
        if sport == "basketball_nba":
            home_ppg = float(home_metrics.get("adjusted_ppg", 0))
            away_ppg = float(away_metrics.get("adjusted_ppg", 0))
            home_fg = float(home_metrics.get("fg_pct", 0))
            away_fg = float(away_metrics.get("fg_pct", 0))
            
    def _compare_metrics(self, home_metrics: Dict, away_metrics: Dict, sport: str) -> float:
        """Compare adjusted metrics between teams, return difference (-15 to +15)"""
        try:
            if sport == "basketball_nba":
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
            
            elif sport == "americanfootball_nfl":
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
            
            elif sport in ["americanfootball_ncaaf", "basketball_ncaab", "basketball_wncaab", "basketball_wnba"]:
                # NCAA/WNBA use same metrics as their pro counterparts
                if "basketball" in sport:
                    home_ppg = float(home_metrics.get("adjusted_ppg", 0))
                    away_ppg = float(away_metrics.get("adjusted_ppg", 0))
                    home_fg = float(home_metrics.get("fg_pct", 0))
                    away_fg = float(away_metrics.get("fg_pct", 0))
                    
                    ppg_diff = (home_ppg - away_ppg) / 5
                    fg_diff = (home_fg - away_fg) * 20
                    
                    return (ppg_diff + fg_diff) / 2
                else:  # NCAAF
                    home_yards = float(home_metrics.get("adjusted_total_yards", 0))
                    away_yards = float(away_metrics.get("adjusted_total_yards", 0))
                    
                    return (home_yards - away_yards) / 50
            
            elif sport == "baseball_mlb":
                # MLB stats not yet supported - ESPN doesn't provide consistent team stats
                self._emit_unsupported_sport_metric(sport)
                return 0.0
            
            # Unknown sport
            self._emit_unsupported_sport_metric(sport)
            return 0.0
            
        except Exception as e:
            logger.error(f"Error comparing metrics: {e}")
            return 0.0
    
    def _emit_unsupported_sport_metric(self, sport: str):
        """Emit CloudWatch metric for unsupported sport"""
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


class ModelFactory:
    """Factory for creating analysis models"""

    _models = {}

    @classmethod
    def create_model(cls, model_name: str) -> BaseAnalysisModel:
        """Create and return a model instance"""
        if model_name == "player_stats":
            from ml.player_stats_model import PlayerStatsModel
            return PlayerStatsModel()
        
        if model_name == "fundamentals":
            from ml.models.fundamentals import FundamentalsModel
            return FundamentalsModel()
        
        if model_name == "matchup":
            from ml.models.matchup import MatchupModel
            return MatchupModel()
        
        if model_name == "momentum":
            from ml.models.momentum import MomentumModel
            return MomentumModel()
        
        if model_name == "value":
            from ml.models.value import ValueModel
            return ValueModel()
        
        if model_name == "hot_cold":
            from ml.models.hot_cold import HotColdModel
            return HotColdModel()
        
        if model_name == "rest_schedule":
            from ml.models.rest_schedule import RestScheduleModel
            return RestScheduleModel()
        
        if model_name == "injury_aware":
            from ml.models.injury_aware import InjuryAwareModel
            return InjuryAwareModel()
        
        if model_name == "contrarian":
            from ml.models.contrarian import ContrarianModel
            return ContrarianModel()
        
        if model_name == "news":
            from ml.models.news import NewsModel
            return NewsModel()
        
        if model_name == "ensemble":
            from ml.models.ensemble import EnsembleModel
            return EnsembleModel()
        
        if model_name == "consensus":
            from ml.models.consensus import ConsensusModel
            return ConsensusModel()
        
        if model_name not in cls._models:
            raise ValueError(
                f"Unknown model: {model_name}. Available: {['player_stats', 'fundamentals', 'matchup', 'momentum', 'value', 'hot_cold', 'rest_schedule', 'injury_aware', 'contrarian', 'news', 'ensemble', 'consensus']}"
            )

        return cls._models[model_name]()

    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of available model names"""
        return ["player_stats", "fundamentals", "matchup", "momentum", "value", "hot_cold", "rest_schedule", "injury_aware", "contrarian", "news", "ensemble", "consensus"]

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)
