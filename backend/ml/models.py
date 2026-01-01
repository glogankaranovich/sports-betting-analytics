"""
ML Models for Sports Betting Analytics
"""

from typing import Dict, List
from dataclasses import dataclass

@dataclass
class GamePrediction:
    home_win_probability: float
    away_win_probability: float
    confidence_score: float
    value_bets: List[str]

class OddsAnalyzer:
    
    @staticmethod
    def american_to_decimal(american_odds: int) -> float:
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1
    
    @staticmethod
    def decimal_to_probability(decimal_odds: float) -> float:
        return 1 / decimal_odds
    
    def analyze_game(self, game_data: Dict) -> GamePrediction:
        """Analyze a single game and return predictions"""
        
        # Extract moneyline odds from all bookmakers
        home_odds = []
        away_odds = []
        bookmaker_names = []
        
        for item in game_data.get('odds', []):
            bookmaker = item.get('bookmaker')
            markets = item.get('markets', [])
            
            for market in markets:
                if market.get('key') == 'h2h':
                    outcomes = market.get('outcomes', [])
                    if len(outcomes) >= 2:
                        home_odds.append(self.american_to_decimal(int(outcomes[0]['price'])))
                        away_odds.append(self.american_to_decimal(int(outcomes[1]['price'])))
                        bookmaker_names.append(bookmaker)
        
        if not home_odds:
            return GamePrediction(0.5, 0.5, 0.1, [])
        
        # Calculate consensus probabilities
        home_probs = [self.decimal_to_probability(odds) for odds in home_odds]
        away_probs = [self.decimal_to_probability(odds) for odds in away_odds]
        
        # Remove vig and normalize
        avg_home_prob = sum(home_probs) / len(home_probs)
        avg_away_prob = sum(away_probs) / len(away_probs)
        total_prob = avg_home_prob + avg_away_prob
        
        home_prob = avg_home_prob / total_prob
        away_prob = avg_away_prob / total_prob
        
        # Calculate confidence (lower std = higher confidence)
        home_std = self._calculate_std(home_probs)
        away_std = self._calculate_std(away_probs)
        confidence = 1 - (home_std + away_std) / 2
        confidence = max(0.1, min(0.9, confidence))
        
        # Find value bets (5% edge threshold)
        value_bets = []
        for i, bookmaker in enumerate(bookmaker_names):
            home_ev = home_prob - home_probs[i]
            away_ev = away_prob - away_probs[i]
            
            if home_ev > 0.05:
                value_bets.append(f"{bookmaker}_home")
            if away_ev > 0.05:
                value_bets.append(f"{bookmaker}_away")
        
        return GamePrediction(
            home_win_probability=round(home_prob, 3),
            away_win_probability=round(away_prob, 3),
            confidence_score=round(confidence, 3),
            value_bets=value_bets
        )
    
    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation without numpy"""
        if len(values) <= 1:
            return 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5
