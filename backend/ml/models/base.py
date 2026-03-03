"""Base model class for all analysis models"""

import logging
import math
import os
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class BaseModel:
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

    def analyze_game_odds(self, game_id: str, odds_items: List[Dict], game_info: Dict):
        """Analyze game odds and return analysis result"""
        raise NotImplementedError("Subclasses must implement analyze_game_odds")

    def analyze_prop_odds(self, prop_item: Dict):
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
        
        if disagreement > 2.0 and confidence > 0.7:
            return {"is_inefficient": True, "disagreement": disagreement, "edge": "STRONG"}
        elif disagreement > 1.0 and confidence > 0.65:
            return {"is_inefficient": True, "disagreement": disagreement, "edge": "MODERATE"}
        
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
