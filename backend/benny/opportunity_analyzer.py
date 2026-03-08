"""Opportunity analysis for betting decisions"""
from typing import Dict, Any, List
from decimal import Decimal


class OpportunityAnalyzer:
    """Analyzes betting opportunities and calculates expected value"""
    
    MIN_EV = 0.05
    
    def __init__(self, learning_engine):
        self.learning_engine = learning_engine
    
    def calculate_expected_value(self, confidence: float, odds: float) -> float:
        """Calculate expected value for a bet"""
        if odds > 0:
            payout_multiplier = 1 + (odds / 100)
        else:
            payout_multiplier = 1 + (100 / abs(odds))
        return (confidence * payout_multiplier) - 1
    
    def filter_opportunities(self, opportunities: List[Dict[str, Any]], bankroll: Decimal) -> List[Dict[str, Any]]:
        """Filter opportunities based on thresholds and bankroll"""
        filtered = []
        
        for opp in opportunities:
            sport = opp.get("sport", "")
            market = opp.get("market_key", "h2h")
            confidence = opp.get("confidence", 0)
            ev = opp.get("expected_value", 0)
            
            # Get adaptive threshold
            threshold = self.learning_engine.get_adaptive_threshold(sport, market)
            
            # Filter by confidence and EV
            if confidence >= threshold and ev >= self.MIN_EV:
                filtered.append(opp)
        
        return filtered
    
    def rank_opportunities(self, opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Rank opportunities by expected value"""
        return sorted(opportunities, key=lambda x: x.get("expected_value", 0), reverse=True)
