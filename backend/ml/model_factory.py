"""Model Factory for creating ML model instances"""

import logging
from typing import List

logger = logging.getLogger(__name__)


class ModelFactory:
    """Factory for creating analysis models"""

    _models = {}

    @classmethod
    def create_model(cls, model_name: str):
        """Create and return a model instance"""
        if model_name == "player_stats":
            from ml.models.player_stats import PlayerStatsModel
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
        
        raise ValueError(
            f"Unknown model: {model_name}. Available: {cls.get_available_models()}"
        )

    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of available model names"""
        return [
            "player_stats", "fundamentals", "matchup", "momentum", "value",
            "hot_cold", "rest_schedule", "injury_aware", "contrarian",
            "news", "ensemble", "consensus"
        ]
