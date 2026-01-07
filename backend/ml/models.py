"""
ML Models for Sports Betting Analytics
"""

from typing import Dict, List
from dataclasses import dataclass
import math
from abc import ABC, abstractmethod


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


class BaseAnalysisModel(ABC):
    """Base class for all analysis models"""

    @abstractmethod
    def analyze_game(self, game_data: Dict) -> GameAnalysis:
        """Analyze a game and return analysis"""
        pass

    @abstractmethod
    def analyze_prop(self, prop_data: Dict) -> PropAnalysis:
        """Analyze a prop bet and return analysis"""
        pass

    def american_to_decimal(self, american_odds: int) -> float:
        """Convert American odds to decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    def decimal_to_probability(self, decimal_odds: float) -> float:
        """Convert decimal odds to implied probability"""
        return 1 / decimal_odds

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)


class ConsensusModel(BaseAnalysisModel):
    """Consensus model that averages all bookmaker odds"""

    def analyze_game(self, game_data: Dict) -> GameAnalysis:
        """Analyze a game using consensus of all bookmaker odds"""
        home_odds = []
        away_odds = []
        bookmaker_names = []

        # Get all bookmaker odds for this game
        bookmaker_items = game_data.get("bookmakers", [])
        home_team = game_data.get("home_team")
        away_team = game_data.get("away_team")

        for item in bookmaker_items:
            if item.get("market_key") == "h2h":
                outcomes = item.get("outcomes", [])
                bookmaker_name = item.get("bookmaker")

                if len(outcomes) >= 2 and bookmaker_name:
                    home_outcome = next(
                        (o for o in outcomes if o["name"] == home_team), None
                    )
                    away_outcome = next(
                        (o for o in outcomes if o["name"] == away_team), None
                    )

                    if home_outcome and away_outcome:
                        home_odds.append(
                            self.american_to_decimal(int(home_outcome["price"]))
                        )
                        away_odds.append(
                            self.american_to_decimal(int(away_outcome["price"]))
                        )
                        bookmaker_names.append(bookmaker_name)

        if not home_odds:
            return GameAnalysis(
                game_id=game_data.get("game_id", "unknown"),
                sport=game_data.get("sport", "unknown"),
                home_win_probability=0.5,
                away_win_probability=0.5,
                confidence_score=0.1,
                value_bets=[],
            )

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

        return GameAnalysis(
            game_id=game_data.get("game_id", "unknown"),
            sport=game_data.get("sport", "unknown"),
            home_win_probability=home_prob,
            away_win_probability=away_prob,
            confidence_score=confidence,
            value_bets=value_bets,
        )

    def analyze_prop(self, prop_data: Dict) -> PropAnalysis:
        """Analyze a prop bet using consensus of all bookmaker odds"""
        over_odds = []
        under_odds = []
        bookmaker_names = []

        bookmaker_items = prop_data.get("bookmakers", [])

        for item in bookmaker_items:
            outcomes = item.get("outcomes", [])
            bookmaker_name = item.get("bookmaker")

            if len(outcomes) >= 2 and bookmaker_name:
                over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
                under_outcome = next(
                    (o for o in outcomes if o["name"] == "Under"), None
                )

                if over_outcome and under_outcome:
                    over_odds.append(
                        self.american_to_decimal(int(over_outcome["price"]))
                    )
                    under_odds.append(
                        self.american_to_decimal(int(under_outcome["price"]))
                    )
                    bookmaker_names.append(bookmaker_name)

        if not over_odds:
            return PropAnalysis(
                game_id=prop_data.get("event_id", "unknown"),
                sport=prop_data.get("sport", "unknown"),
                player_name=prop_data.get("player_name", "unknown"),
                prop_type=prop_data.get("market_key", "unknown"),
                line=float(prop_data.get("point", 0)),
                over_probability=0.5,
                under_probability=0.5,
                confidence_score=0.1,
                value_bets=[],
            )

        # Calculate consensus probabilities
        over_probs = [self.decimal_to_probability(odds) for odds in over_odds]
        under_probs = [self.decimal_to_probability(odds) for odds in under_odds]

        # Remove vig and normalize
        avg_over_prob = sum(over_probs) / len(over_probs)
        avg_under_prob = sum(under_probs) / len(under_probs)
        total_prob = avg_over_prob + avg_under_prob

        over_prob = avg_over_prob / total_prob
        under_prob = avg_under_prob / total_prob

        # Calculate confidence
        over_std = self._calculate_std(over_probs)
        under_std = self._calculate_std(under_probs)
        confidence = 1 - (over_std + under_std) / 2
        confidence = max(0.1, min(0.9, confidence))

        # Find value bets
        value_bets = []
        for i, bookmaker in enumerate(bookmaker_names):
            over_ev = over_prob - over_probs[i]
            under_ev = under_prob - under_probs[i]

            if over_ev > 0.05:
                value_bets.append(f"{bookmaker}_over")
            if under_ev > 0.05:
                value_bets.append(f"{bookmaker}_under")

        return PropAnalysis(
            game_id=prop_data.get("event_id", "unknown"),
            sport=prop_data.get("sport", "unknown"),
            player_name=prop_data.get("player_name", "unknown"),
            prop_type=prop_data.get("market_key", "unknown"),
            line=float(prop_data.get("point", 0)),
            over_probability=over_prob,
            under_probability=under_prob,
            confidence_score=confidence,
            value_bets=value_bets,
        )


class ModelFactory:
    """Factory to create analysis models"""

    @staticmethod
    def create_model(model_type: str) -> BaseAnalysisModel:
        """Create a model instance based on type"""
        if model_type == "consensus":
            return ConsensusModel()
        else:
            raise ValueError(f"Unknown model type: {model_type}")
