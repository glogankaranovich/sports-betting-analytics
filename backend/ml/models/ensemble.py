"""Ensemble Model - Weighted combination of all models"""

import logging
from typing import Dict, List

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class EnsembleModel(BaseModel):
    """Ensemble model: Weighted combination of all models using dynamic weighting"""

    def __init__(self):
        from ml.dynamic_weighting import DynamicModelWeighting
        from ml.player_stats_model import PlayerStatsModel
        from ml.models.value import ValueModel
        from ml.models.momentum import MomentumModel
        from ml.models.contrarian import ContrarianModel
        from ml.models.hot_cold import HotColdModel
        from ml.models.rest_schedule import RestScheduleModel
        from ml.models.matchup import MatchupModel
        from ml.models.injury_aware import InjuryAwareModel
        from ml.models.news import NewsModel

        self.weighting = DynamicModelWeighting()
        self.models = {
            "value": ValueModel(),
            "momentum": MomentumModel(),
            "contrarian": ContrarianModel(),
            "hot_cold": HotColdModel(),
            "rest_schedule": RestScheduleModel(),
            "matchup": MatchupModel(),
            "injury_aware": InjuryAwareModel(),
            "news": NewsModel(),
            "player_stats": PlayerStatsModel(),
        }

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        try:
            sport = game_info.get("sport")

            predictions = {}
            for model_name, model in self.models.items():
                result = model.analyze_game_odds(game_id, odds_items, game_info)
                if result:
                    predictions[model_name] = result

            if not predictions:
                return None

            weights = self.weighting.get_model_weights(
                sport, "game", list(predictions.keys())
            )

            weighted_confidence = sum(
                predictions[model].confidence * weights[model]
                for model in predictions.keys()
            )

            best_model = max(weights.items(), key=lambda x: x[1])[0]
            best_prediction = predictions[best_model]

            top_models = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
            model_list = ", ".join([f"{model} ({weight*100:.1f}%)" for model, weight in top_models])

            return AnalysisResult(
                game_id=game_id,
                model="ensemble",
                analysis_type="game",
                sport=sport,
                home_team=game_info.get("home_team"),
                away_team=game_info.get("away_team"),
                commence_time=game_info.get("commence_time"),
                prediction=best_prediction.prediction,
                confidence=weighted_confidence,
                reasoning=f"Combined prediction from {len(predictions)} models: {model_list}",
                recommended_odds=-110,
            )
        except Exception as e:
            logger.error(f"Error in Ensemble game analysis: {e}")
            return None

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        try:
            sport = prop_item.get("sport")

            predictions = {}
            for model_name, model in self.models.items():
                result = model.analyze_prop_odds(prop_item)
                if result:
                    predictions[model_name] = result

            if not predictions:
                return None

            weights = self.weighting.get_model_weights(
                sport, "prop", list(predictions.keys())
            )

            weighted_confidence = sum(
                predictions[model].confidence * weights[model]
                for model in predictions.keys()
            )

            best_model = max(weights.items(), key=lambda x: x[1])[0]
            best_prediction = predictions[best_model]
            
            top_models = sorted(weights.items(), key=lambda x: x[1], reverse=True)[:3]
            model_list = ", ".join([f"{model} ({weight*100:.1f}%)" for model, weight in top_models])

            return AnalysisResult(
                game_id=best_prediction.game_id,
                model="ensemble",
                analysis_type="prop",
                sport=sport,
                home_team=best_prediction.home_team,
                away_team=best_prediction.away_team,
                commence_time=best_prediction.commence_time,
                player_name=best_prediction.player_name,
                market_key=best_prediction.market_key,
                prediction=best_prediction.prediction,
                confidence=weighted_confidence,
                reasoning=f"Combined prediction from {len(predictions)} models: {model_list}",
                recommended_odds=-110,
            )
        except Exception as e:
            logger.error(f"Error in Ensemble prop analysis: {e}")
            return None
