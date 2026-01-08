"""
ML Models for Sports Betting Analytics
"""

from typing import Dict, List, Any
from dataclasses import dataclass
import math
from datetime import datetime


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


@dataclass
class AnalysisResult:
    """Standardized analysis result for DynamoDB storage"""

    game_id: str
    model: str
    analysis_type: str  # "game" or "prop"
    sport: str
    prediction: str
    confidence: float
    reasoning: str
    home_team: str = None
    away_team: str = None
    commence_time: str = None
    player_name: str = None
    bookmaker: str = None

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format with GSI attributes"""
        return {
            "pk": f"ANALYSIS#{self.sport}#{self.game_id}#{self.bookmaker}",
            "sk": f"{self.model}#{self.analysis_type}#LATEST",
            "analysis_pk": f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}",  # AnalysisGSI partition key
            "analysis_time_pk": f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}",  # AnalysisTimeGSI partition key
            "commence_time": self.commence_time,  # Sort key for AnalysisTimeGSI
            "model_type": f"{self.model}#{self.analysis_type}",  # Sort key for AnalysisGSI
            "analysis_type": self.analysis_type,
            "model": self.model,
            "game_id": self.game_id,
            "sport": self.sport,
            "bookmaker": self.bookmaker,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "player_name": self.player_name,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "created_at": datetime.utcnow().isoformat(),
            "latest": True,
        }


class BaseAnalysisModel:
    """Base class for all analysis models"""

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


class ConsensusModel(BaseAnalysisModel):
    """Consensus model: Average across all bookmakers"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        spreads = []
        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    spreads.append(float(item["outcomes"][0].get("point", 0)))

        if not spreads:
            return None

        avg_spread = sum(spreads) / len(spreads)
        confidence = min(0.95, 0.6 + (len(spreads) * 0.05))

        return AnalysisResult(
            game_id=game_id,
            model="consensus",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=f"{game_info.get('home_team')} {avg_spread:+.1f}",
            confidence=confidence,
            reasoning=f"Consensus across {len(spreads)} bookmakers: {avg_spread:+.1f}",
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        # Simplified prop analysis for now
        return None


class ValueModel(BaseAnalysisModel):
    """Value model: Find best odds discrepancies"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        spreads = []
        current_bookmaker = game_info.get("bookmaker")

        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    spread = float(item["outcomes"][0].get("point", 0))
                    price = float(item["outcomes"][0].get("price", 0))
                    spreads.append((spread, price))

        if not spreads:
            return None

        # For value model, just use the first spread since we're analyzing per-bookmaker
        selected_spread = spreads[0]
        avg_spread = sum(s[0] for s in spreads) / len(spreads)
        confidence = 0.7 if abs(selected_spread[0] - avg_spread) > 1.0 else 0.5

        return AnalysisResult(
            game_id=game_id,
            model="value",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=f"{game_info.get('home_team')} {selected_spread[0]:+.1f} @ {current_bookmaker}",
            confidence=confidence,
            reasoning=f"Value bet: {selected_spread[0]:+.1f} vs consensus {avg_spread:+.1f}",
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        return None


class MomentumModel(BaseAnalysisModel):
    """Momentum model: Based on recent odds movement"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        latest_item = max(odds_items, key=lambda x: x.get("updated_at", ""))

        if "spreads" not in latest_item.get("sk", "") or "outcomes" not in latest_item:
            return None

        if len(latest_item["outcomes"]) < 2:
            return None

        spread = float(latest_item["outcomes"][0].get("point", 0))
        confidence = 0.75

        return AnalysisResult(
            game_id=game_id,
            model="momentum",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=f"{game_info.get('home_team')} {spread:+.1f}",
            confidence=confidence,
            reasoning=f"Momentum play: Latest line {spread:+.1f} from {latest_item.get('bookmaker')}",
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        return None


class ModelFactory:
    """Factory for creating analysis models"""

    _models = {
        "consensus": ConsensusModel,
        "value": ValueModel,
        "momentum": MomentumModel,
    }

    @classmethod
    def create_model(cls, model_name: str) -> BaseAnalysisModel:
        """Create and return a model instance"""
        if model_name not in cls._models:
            raise ValueError(
                f"Unknown model: {model_name}. Available: {list(cls._models.keys())}"
            )

        return cls._models[model_name]()

    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of available model names"""
        return list(cls._models.keys())

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
