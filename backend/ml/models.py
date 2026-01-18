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
        # For props, include player_name in PK to avoid collisions with game analyses
        if self.analysis_type == "prop" and self.player_name:
            pk = f"ANALYSIS#{self.sport}#{self.game_id}#{self.player_name}#{self.bookmaker}"
            analysis_pk = f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#prop"
            analysis_time_pk = (
                f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#prop"
            )
        else:
            pk = f"ANALYSIS#{self.sport}#{self.game_id}#{self.bookmaker}"
            analysis_pk = f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#game"
            analysis_time_pk = (
                f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#game"
            )

        return {
            "pk": pk,
            "sk": f"{self.model}#{self.analysis_type}#LATEST",
            "analysis_pk": analysis_pk,  # AnalysisGSI partition key
            "analysis_time_pk": analysis_time_pk,  # AnalysisTimeGSI partition key
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

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)


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
        """Analyze prop odds using consensus approach"""
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            # Convert American odds to probabilities
            over_decimal = self.american_to_decimal(int(over_outcome["price"]))
            under_decimal = self.american_to_decimal(int(under_outcome["price"]))

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            # Remove vig and normalize
            total_prob = over_prob + under_prob
            over_prob_fair = over_prob / total_prob
            under_prob_fair = under_prob / total_prob

            # Determine prediction based on higher probability
            if over_prob_fair > under_prob_fair:
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = over_prob_fair
            else:
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = under_prob_fair

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                bookmaker=prop_item.get("bookmaker"),
                model="consensus",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                prediction=prediction,
                confidence=confidence,
                reasoning=f"Consensus analysis: {prediction} with {confidence:.1%} confidence (Over: {over_prob_fair:.1%}, Under: {under_prob_fair:.1%})",
            )

        except Exception as e:
            print(f"Error analyzing prop odds: {e}")
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
        """Analyze prop odds looking for value opportunities"""
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            # Convert American odds to probabilities
            over_decimal = self.american_to_decimal(int(over_outcome["price"]))
            under_decimal = self.american_to_decimal(int(under_outcome["price"]))

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            # Look for value - if one side has significantly better odds
            total_prob = over_prob + under_prob
            vig = total_prob - 1.0

            # Value model looks for low vig situations or line discrepancies
            if vig < 0.05:  # Low vig = potential value
                confidence = 0.8
                if over_prob > under_prob:
                    prediction = f"Over {prop_item.get('point', 'N/A')} (Value)"
                    reasoning = f"Low vig opportunity: {vig:.1%} vig, Over favored"
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')} (Value)"
                    reasoning = f"Low vig opportunity: {vig:.1%} vig, Under favored"
            else:
                confidence = 0.6
                # Look for the side with better implied odds
                over_prob_fair = over_prob / total_prob
                under_prob_fair = under_prob / total_prob

                if over_prob_fair > 0.55:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = f"Value play: Over {over_prob_fair:.1%} vs Under {under_prob_fair:.1%}"
                elif under_prob_fair > 0.55:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = f"Value play: Under {under_prob_fair:.1%} vs Over {over_prob_fair:.1%}"
                else:
                    return None  # No clear value

            # Extract player name
            player_name = (
                prop_item.get("description", "").split(" - ")[0]
                if " - " in prop_item.get("description", "")
                else "Unknown Player"
            )

            return AnalysisResult(
                game_id=prop_item.get("pk", "").replace("PROP#", "").split("#")[1]
                if "#" in prop_item.get("pk", "")
                else "unknown",
                model="value",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=player_name,
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
            )

        except Exception as e:
            print(f"Error analyzing prop odds: {e}")
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
        """Analyze prop odds based on recent line movement"""
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            # For momentum model, we focus on the most recent odds
            # In a real implementation, we'd compare with historical odds
            over_price = int(over_outcome["price"])
            under_price = int(under_outcome["price"])

            # Convert to probabilities
            over_decimal = self.american_to_decimal(over_price)
            under_decimal = self.american_to_decimal(under_price)

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            # Momentum model assumes recent movement indicates sharp money
            # For now, we'll favor the side with better odds (indicating recent movement)
            if over_price > -110:  # Over is getting worse odds = money on Under
                prediction = f"Under {prop_item.get('point', 'N/A')} (Momentum)"
                confidence = 0.7
                reasoning = f"Momentum play: Over odds moved to {over_price}, indicating Under action"
            elif under_price > -110:  # Under is getting worse odds = money on Over
                prediction = f"Over {prop_item.get('point', 'N/A')} (Momentum)"
                confidence = 0.7
                reasoning = f"Momentum play: Under odds moved to {under_price}, indicating Over action"
            else:
                # No clear momentum, pick the favorite
                if over_prob > under_prob:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    confidence = 0.6
                    reasoning = (
                        f"Latest odds favor Over ({over_price} vs {under_price})"
                    )
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    confidence = 0.6
                    reasoning = (
                        f"Latest odds favor Under ({under_price} vs {over_price})"
                    )

            # Extract player name
            player_name = (
                prop_item.get("description", "").split(" - ")[0]
                if " - " in prop_item.get("description", "")
                else "Unknown Player"
            )

            return AnalysisResult(
                game_id=prop_item.get("pk", "").replace("PROP#", "").split("#")[1]
                if "#" in prop_item.get("pk", "")
                else "unknown",
                model="momentum",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=player_name,
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
            )

        except Exception as e:
            print(f"Error analyzing prop odds: {e}")
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
