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
    market_key: str = None  # For props: player_points, player_assists, etc.
    recommended_odds: int = None  # American odds for ROI calculation

    @property
    def roi(self) -> float:
        """Calculate expected ROI"""
        if not self.recommended_odds:
            return None
        odds = self.recommended_odds
        roi_multiplier = 100 / abs(odds) if odds < 0 else odds / 100
        return round(
            (self.confidence * roi_multiplier - (1 - self.confidence)) * 100, 1
        )

    @property
    def risk_level(self) -> str:
        """Determine risk level based on confidence"""
        if self.confidence >= 0.65:
            return "conservative"
        elif self.confidence >= 0.55:
            return "moderate"
        else:
            return "aggressive"

    @property
    def implied_probability(self) -> float:
        """Calculate implied probability from odds"""
        if not self.recommended_odds:
            return None
        odds = self.recommended_odds
        implied_prob = abs(odds) / (abs(odds) + 100) if odds < 0 else 100 / (odds + 100)
        return round(implied_prob * 100, 1)

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

        item = {
            "pk": pk,
            "sk": f"{self.model}#{self.analysis_type}#LATEST",
            "analysis_pk": analysis_pk,  # AnalysisGSI partition key
            "analysis_time_pk": analysis_time_pk,  # AnalysisTimeGSI partition key
            "model_type": f"{self.model}#{self.analysis_type}",  # Sort key for AnalysisGSI
            "analysis_type": self.analysis_type,
            "model": self.model,
            "game_id": self.game_id,
            "sport": self.sport,
            "bookmaker": self.bookmaker,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "player_name": self.player_name,
            "market_key": self.market_key,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "recommended_odds": self.recommended_odds,
            "roi": self.roi,
            "risk_level": self.risk_level,
            "implied_probability": self.implied_probability,
            "created_at": datetime.utcnow().isoformat(),
            "latest": True,
        }
        
        # Only include commence_time if it's not None (required for GSI)
        if self.commence_time:
            item["commence_time"] = self.commence_time
        else:
            # Use a default far future date if commence_time is missing
            item["commence_time"] = "9999-12-31T23:59:59Z"
        
        return item


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


class ConsensusModel(BaseAnalysisModel):
    """Consensus model: Average across all bookmakers with Elo adjustments"""
    
    def __init__(self):
        super().__init__()
        self.elo_calculator = EloCalculator()
        self.dynamodb = boto3.resource("dynamodb")
        table_name = os.getenv("DYNAMODB_TABLE")
        self.table = self.dynamodb.Table(table_name) if table_name else None

    def _get_line_movement(self, game_id: str, bookmaker: str = "fanduel") -> Dict[str, Any]:
        """Get line movement for a game"""
        if not self.table:
            return None
        
        pk = f"GAME#{game_id}"
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND begins_with(sk, :sk_prefix)",
                ExpressionAttributeValues={
                    ":pk": pk,
                    ":sk_prefix": f"{bookmaker}#spreads#"
                },
                ScanIndexForward=True
            )
            
            items = response.get("Items", [])
            if len(items) < 2:
                return None
            
            opening = next((item for item in items if "#LATEST" not in item["sk"]), None)
            current = next((item for item in items if "#LATEST" in item["sk"]), None)
            
            if not opening or not current or len(opening.get("outcomes", [])) < 2:
                return None
            
            opening_spread = float(opening["outcomes"][0].get("point", 0))
            current_spread = float(current["outcomes"][0].get("point", 0))
            movement = current_spread - opening_spread
            
            opening_price = int(opening["outcomes"][0].get("price", -110))
            current_price = int(current["outcomes"][0].get("price", -110))
            
            is_rlm = (movement > 0 and current_price < opening_price) or \
                     (movement < 0 and current_price > opening_price)
            
            return {
                "movement": movement,
                "is_rlm": is_rlm,
                "opening_spread": opening_spread,
                "current_spread": current_spread
            }
        except Exception as e:
            logger.error(f"Error getting line movement: {e}")
            return None

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        spreads = []
        odds_prices = []
        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    spreads.append(float(item["outcomes"][0].get("point", 0)))
                    odds_prices.append(int(item["outcomes"][0].get("price", -110)))

        if not spreads:
            return None

        avg_spread = sum(spreads) / len(spreads)
        avg_odds = int(sum(odds_prices) / len(odds_prices)) if odds_prices else -110
        confidence = min(0.95, 0.6 + (len(spreads) * 0.05))
        
        # Get Elo ratings for both teams
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        
        try:
            home_elo = self.elo_calculator.get_team_rating(sport, home_team)
            away_elo = self.elo_calculator.get_team_rating(sport, away_team)
            elo_diff = home_elo - away_elo
            
            # Adjust confidence based on Elo alignment with spread
            # Positive spread = home favored, positive elo_diff = home stronger
            elo_context = ""
            if abs(elo_diff) > 100:
                if (avg_spread < 0 and elo_diff > 50) or (avg_spread > 0 and elo_diff < -50):
                    # Elo agrees with spread
                    confidence = min(confidence + 0.05, 0.95)
                    elo_context = f" Elo ratings confirm: {home_team} {home_elo:.0f} vs {away_team} {away_elo:.0f}."
                elif (avg_spread < 0 and elo_diff < -50) or (avg_spread > 0 and elo_diff > 50):
                    # Elo disagrees with spread
                    confidence = max(confidence - 0.05, 0.55)
                    elo_context = f" Elo ratings suggest caution: {home_team} {home_elo:.0f} vs {away_team} {away_elo:.0f}."
        except Exception as e:
            logger.error(f"Error getting Elo ratings: {e}")
            elo_context = ""  # Set default value on error

        # Check line movement
        line_context = ""
        line_movement = self._get_line_movement(game_id)
        if line_movement:
            if line_movement["is_rlm"]:
                confidence = min(confidence + 0.05, 0.95)
                line_context = f" Sharp money detected (RLM)."
            elif abs(line_movement["movement"]) > 1.5:
                line_context = f" Line moved {abs(line_movement['movement']):.1f} points."

        # Adjust confidence based on historical performance
        confidence = self._adjust_confidence(confidence, "consensus", sport)

        # Log market inefficiency if significant disagreement
        if self.inefficiency_tracker and line_movement:
            market_spread = line_movement.get("current_spread", avg_spread)
            if abs(avg_spread - market_spread) > 1.0:
                self.inefficiency_tracker.log_disagreement(
                    game_id=game_id,
                    model="consensus",
                    sport=sport,
                    model_prediction=f"{home_team} {avg_spread:+.1f}",
                    model_spread=avg_spread,
                    market_spread=market_spread,
                    confidence=confidence,
                )

        return AnalysisResult(
            game_id=game_id,
            model="consensus",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=f"{home_team} {avg_spread:+.1f}",
            confidence=confidence,
            reasoning=f"{len(spreads)} sportsbooks agree: {home_team} is favored by {abs(avg_spread):.1f} points. Average payout odds: {avg_odds:+d}.{elo_context}{line_context}",
            recommended_odds=avg_odds,
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
                bookmaker="consensus",  # Will be overridden per bookmaker
                model="consensus",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                market_key=prop_item.get("market_key"),
                prediction=prediction,
                confidence=confidence,
                reasoning=f"{len(prop_item.get('bookmakers', []))} sportsbooks predict: {prediction}. They're {confidence*100:.0f}% confident in this outcome",
                recommended_odds=-110,
            )

        except Exception as e:
            logger.error(f"Error analyzing prop odds: {e}", exc_info=True)
            return None


class ValueModel(BaseAnalysisModel):
    """Value model: Find best odds discrepancies"""

    def __init__(self):
        super().__init__()
        self.elo_calculator = EloCalculator()

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
        
        # Validate with Elo ratings
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        
        try:
            home_elo = self.elo_calculator.get_team_rating(sport, home_team)
            away_elo = self.elo_calculator.get_team_rating(sport, away_team)
            elo_diff = home_elo - away_elo
            
            # Check if value bet aligns with Elo
            if (selected_spread[0] < avg_spread and elo_diff > 50) or \
               (selected_spread[0] > avg_spread and elo_diff < -50):
                confidence = min(confidence + 0.05, 0.95)
        except Exception as e:
            logger.error(f"Error getting Elo ratings: {e}")
        
        confidence = self._adjust_confidence(confidence, "value", sport)

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
            reasoning=f"Better odds found: {current_bookmaker} offers {abs(selected_spread[0]):.1f} point spread vs average of {abs(avg_spread):.1f}. That's a {abs(selected_spread[0] - avg_spread):.1f} point difference",
            recommended_odds=-110,
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

            # Remove vig to get fair probabilities
            over_prob_fair = over_prob / total_prob
            under_prob_fair = under_prob / total_prob

            # Value model looks for low vig situations (better value for bettors)
            if vig < 0.06:  # Low vig (< 6%) = good value
                confidence = 0.75
                if over_prob_fair > under_prob_fair:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Great odds: Sportsbook is offering better than usual pricing. Over is {over_prob_fair:.0%} likely based on the odds"
                    )
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Great odds: Sportsbook is offering better than usual pricing. Under is {under_prob_fair:.0%} likely based on the odds"
                    )
            elif vig < 0.08:  # Moderate vig (6-8%) = decent value
                confidence = 0.65
                if over_prob_fair > 0.52:  # Slight edge
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Good odds: Over has a slight edge at {over_prob_fair:.0%} probability. Better pricing than typical"
                    )
                elif under_prob_fair > 0.52:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = (
                        f"Good odds: Under has a slight edge at {under_prob_fair:.0%} probability. Better pricing than typical"
                    )
                else:
                    return None  # Too close to call
            else:
                # High vig - only recommend if there's a clear edge
                if over_prob_fair > 0.55:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    confidence = 0.6
                    reasoning = f"Decent odds: Over is {over_prob_fair:.0%} likely. Worth considering despite higher sportsbook fees"
                elif under_prob_fair > 0.55:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    confidence = 0.6
                    reasoning = f"Decent odds: Under is {under_prob_fair:.0%} likely. Worth considering despite higher sportsbook fees"
                else:
                    return None  # No value in high vig situation

            # Adjust confidence based on historical performance
            confidence = self._adjust_confidence(confidence, "value", prop_item.get("sport"))

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                model="value",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                market_key=prop_item.get("market_key"),
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
                recommended_odds=-110,
            )

        except Exception as e:
            logger.error(f"Error analyzing prop odds: {e}", exc_info=True)
            return None


class MomentumModel(BaseAnalysisModel):
    """Momentum model: Based on recent odds movement with fatigue adjustments"""
    
    def __init__(self):
        super().__init__()
        self.fatigue_calculator = TravelFatigueCalculator()
        self.elo_calculator = EloCalculator()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        # Filter for spread items and sort by timestamp
        spread_items = [
            item
            for item in odds_items
            if "spreads" in item.get("sk", "") and "outcomes" in item
        ]

        if len(spread_items) < 2:
            return None  # Need at least 2 data points for momentum

        # Sort by updated_at timestamp
        spread_items.sort(key=lambda x: x.get("updated_at", ""))

        # Get oldest and newest spreads
        oldest = spread_items[0]
        newest = spread_items[-1]

        if len(oldest.get("outcomes", [])) < 2 or len(newest.get("outcomes", [])) < 2:
            return None

        old_spread = float(oldest["outcomes"][0].get("point", 0))
        new_spread = float(newest["outcomes"][0].get("point", 0))

        # Calculate movement
        movement = new_spread - old_spread
        
        # Get fatigue data
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        game_date = game_info.get("commence_time")
        
        fatigue_context = ""
        try:
            home_fatigue = self.fatigue_calculator.calculate_fatigue_score(home_team, sport, game_date)
            away_fatigue = self.fatigue_calculator.calculate_fatigue_score(away_team, sport, game_date)
            
            # Adjust confidence based on fatigue
            fatigue_diff = away_fatigue['fatigue_score'] - home_fatigue['fatigue_score']
            
            if abs(fatigue_diff) > 30:
                if fatigue_diff > 0:
                    # Away team more fatigued, home advantage
                    fatigue_context = f" {away_team} fatigued (score: {away_fatigue['fatigue_score']}, {away_fatigue['days_rest']}d rest)."
                else:
                    # Home team more fatigued
                    fatigue_context = f" {home_team} fatigued (score: {home_fatigue['fatigue_score']}, {home_fatigue['days_rest']}d rest)."
        except Exception as e:
            logger.error(f"Error calculating fatigue: {e}")

        # Higher confidence if significant movement
        if abs(movement) > 1.0:
            confidence = 0.8
            reasoning = f"Big line shift: Spread moved from {abs(old_spread):.1f} to {abs(new_spread):.1f} points ({abs(movement):.1f} point change). Professional bettors are likely driving this move.{fatigue_context}"
        elif abs(movement) > 0.5:
            confidence = 0.7
            reasoning = f"Line is moving: Spread changed from {abs(old_spread):.1f} to {abs(new_spread):.1f} points. Sportsbooks adjusting based on betting patterns.{fatigue_context}"
        else:
            confidence = 0.6
            reasoning = f"Small line adjustment: Spread moved slightly from {abs(old_spread):.1f} to {abs(new_spread):.1f} points. Minor market change.{fatigue_context}"

        # Validate with Elo ratings
        try:
            home_elo = self.elo_calculator.get_team_rating(sport, home_team)
            away_elo = self.elo_calculator.get_team_rating(sport, away_team)
            elo_diff = home_elo - away_elo
            
            # Check if line movement aligns with Elo
            if (movement < 0 and elo_diff > 50) or (movement > 0 and elo_diff < -50):
                confidence = min(confidence + 0.05, 0.95)
        except Exception as e:
            logger.error(f"Error getting Elo ratings: {e}")

        confidence = self._adjust_confidence(confidence, "momentum", sport)

        return AnalysisResult(
            game_id=game_id,
            model="momentum",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_date,
            prediction=f"{home_team} {new_spread:+.1f}",
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds based on line movement - requires historical data"""
        # Note: This is a simplified version since we're analyzing a single prop_item
        # In a real implementation with historical data, we'd query multiple timestamps
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            over_price = int(over_outcome["price"])
            under_price = int(under_outcome["price"])

            # Convert to probabilities
            over_decimal = self.american_to_decimal(over_price)
            under_decimal = self.american_to_decimal(under_price)

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            # Detect sharp money based on odds imbalance
            # If one side has significantly worse odds, sharp money is on the other side
            if over_price <= -120:  # Over is heavily favored
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = 0.75
                reasoning = (
                    f"Sharp action on Over: {over_price} indicates heavy betting"
                )
            elif under_price <= -120:  # Under is heavily favored
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = 0.75
                reasoning = (
                    f"Sharp action on Under: {under_price} indicates heavy betting"
                )
            elif over_prob > under_prob * 1.1:  # Over has 10%+ edge
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = 0.7
                reasoning = f"Momentum favors Over: {over_price} vs {under_price}"
            elif under_prob > over_prob * 1.1:  # Under has 10%+ edge
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = 0.7
                reasoning = f"Momentum favors Under: {under_price} vs {over_price}"
            else:
                return None  # No clear momentum signal

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                model="momentum",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                market_key=prop_item.get("market_key"),
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
                recommended_odds=-110,
            )

        except Exception as e:
            logger.error(f"Error analyzing prop odds: {e}", exc_info=True)
            return None


class ContrarianModel(BaseAnalysisModel):
    """Contrarian model: Fade the public, follow sharp action with Elo validation"""
    
    def __init__(self):
        super().__init__()
        self.elo_calculator = EloCalculator()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """
        Contrarian approach:
        1. Look for reverse line movement (line moves against public betting)
        2. Identify odds imbalances that suggest sharp action
        3. Fade heavy public favorites
        4. Validate with Elo ratings
        """
        spread_items = []

        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    spread_items.append(item)

        if not spread_items:
            return None

        # Sort by timestamp to track movement
        spread_items.sort(key=lambda x: x.get("updated_at", ""))

        if len(spread_items) < 2:
            # Not enough data for movement analysis, use odds imbalance
            return self._analyze_odds_imbalance(game_id, spread_items[0], game_info)

        # Analyze line movement for reverse line movement
        oldest = spread_items[0]
        newest = spread_items[-1]

        if len(oldest.get("outcomes", [])) < 2 or len(newest.get("outcomes", [])) < 2:
            return None

        old_spread = float(oldest["outcomes"][0].get("point", 0))
        new_spread = float(newest["outcomes"][0].get("point", 0))
        movement = new_spread - old_spread
        
        # Get Elo ratings to validate contrarian play
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        
        elo_context = ""
        elo_boost = 0.0
        try:
            home_elo = self.elo_calculator.get_team_rating(sport, home_team)
            away_elo = self.elo_calculator.get_team_rating(sport, away_team)
            elo_diff = home_elo - away_elo
            
            # Validate contrarian play with Elo
            if abs(elo_diff) > 50:
                # Check if Elo supports the contrarian pick
                if movement > 0 and elo_diff < 0:
                    # Line moving toward away team, Elo says away team is stronger
                    elo_boost = 0.05
                    elo_context = f" Elo confirms: {away_team} ({away_elo:.0f}) > {home_team} ({home_elo:.0f})."
                elif movement < 0 and elo_diff > 0:
                    # Line moving toward home team, Elo says home team is stronger
                    elo_boost = 0.05
                    elo_context = f" Elo confirms: {home_team} ({home_elo:.0f}) > {away_team} ({away_elo:.0f})."
                elif (movement > 0 and elo_diff > 50) or (movement < 0 and elo_diff < -50):
                    # Elo disagrees with contrarian play
                    elo_boost = -0.1
                    elo_context = f" Caution: Elo suggests {home_team if elo_diff > 0 else away_team} is stronger."
        except Exception as e:
            logger.error(f"Error getting Elo ratings: {e}")

        # Contrarian signal: significant line movement suggests sharp action
        if abs(movement) > 1.0:
            # Strong movement = sharp money
            confidence = min(0.75 + elo_boost, 0.85)
            # Bet with the line movement (sharp side)
            if movement > 0:
                prediction = f"{away_team} {-new_spread:+.1f}"
                reasoning = f"Big money moving the line: Spread changed {abs(movement):.1f} points. Going against the crowd and following the big bettors.{elo_context}"
            else:
                prediction = f"{home_team} {new_spread:+.1f}"
                reasoning = f"Big money moving the line: Spread changed {abs(movement):.1f} points. Going against the crowd and following the big bettors.{elo_context}"
        elif abs(movement) > 0.5:
            confidence = min(0.65 + elo_boost, 0.75)
            if movement > 0:
                prediction = f"{away_team} {-new_spread:+.1f}"
                reasoning = f"Line moving: Spread shifted {abs(movement):.1f} points. Smart money taking the opposite side of most bettors.{elo_context}"
            else:
                prediction = f"{home_team} {new_spread:+.1f}"
                reasoning = f"Line moving: Spread shifted {abs(movement):.1f} points. Smart money taking the opposite side of most bettors.{elo_context}"
        else:
            # No significant movement, use odds imbalance
            return self._analyze_odds_imbalance(game_id, newest, game_info)

        return AnalysisResult(
            game_id=game_id,
            model="contrarian",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def _analyze_odds_imbalance(
        self, game_id: str, spread_item: Dict, game_info: Dict
    ) -> AnalysisResult:
        """
        Analyze odds imbalance to detect sharp action
        When one side has worse odds than expected, it suggests sharp money
        """
        outcomes = spread_item.get("outcomes", [])
        if len(outcomes) < 2:
            return None

        home_outcome = outcomes[0]
        away_outcome = outcomes[1]

        home_price = float(home_outcome.get("price", -110))
        away_price = float(away_outcome.get("price", -110))
        home_spread = float(home_outcome.get("point", 0))

        # Calculate vig imbalance
        # Standard is -110/-110, imbalance suggests one-sided action
        price_diff = abs(home_price - away_price)

        if price_diff > 15:
            # Significant imbalance - bet the worse price (sharp side)
            confidence = 0.70
            if home_price < away_price:
                # Home has worse price = sharp money on home
                prediction = f"{game_info.get('home_team')} {home_spread:+.1f}"
                reasoning = f"Uneven odds ({home_price}/{away_price}). Big money is on home team"
            else:
                # Away has worse price = sharp money on away
                prediction = f"{game_info.get('away_team')} {-home_spread:+.1f}"
                reasoning = f"Uneven odds ({home_price}/{away_price}). Big money is on away team"
        elif price_diff > 10:
            confidence = 0.60
            if home_price < away_price:
                prediction = f"{game_info.get('home_team')} {home_spread:+.1f}"
                reasoning = f"Slightly uneven odds ({home_price}/{away_price}). Leaning home"
            else:
                prediction = f"{game_info.get('away_team')} {-home_spread:+.1f}"
                reasoning = f"Slightly uneven odds ({home_price}/{away_price}). Leaning away"
        else:
            # No clear signal, fade the favorite
            confidence = 0.55
            if home_spread < 0:
                # Home is favorite, fade them
                prediction = f"{game_info.get('away_team')} {-home_spread:+.1f}"
                reasoning = f"Betting against the favorite {game_info.get('home_team')}"
            else:
                # Away is favorite, fade them
                prediction = f"{game_info.get('home_team')} {home_spread:+.1f}"
                reasoning = f"Betting against the favorite {game_info.get('away_team')}"

        return AnalysisResult(
            game_id=game_id,
            model="contrarian",
            analysis_type="game",
            sport=game_info.get("sport"),
            home_team=game_info.get("home_team"),
            away_team=game_info.get("away_team"),
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds using contrarian approach"""
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            over_price = float(over_outcome.get("price", -110))
            under_price = float(under_outcome.get("price", -110))

            # Analyze odds imbalance
            price_diff = abs(over_price - under_price)

            if price_diff > 15:
                # Significant imbalance - bet the worse price (sharp side)
                confidence = 0.70
                if over_price < under_price:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = f"Big money on Over. Uneven odds: {over_price}/{under_price}"
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = f"Big money on Under. Uneven odds: {over_price}/{under_price}"
            elif price_diff > 10:
                confidence = 0.60
                if over_price < under_price:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = f"Leaning Over based on odds: {over_price}/{under_price}"
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = f"Leaning Under based on odds: {over_price}/{under_price}"
            else:
                # No clear signal, fade the public (assume public likes overs)
                confidence = 0.55
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                reasoning = "Going against the crowd (most people bet overs)"

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                bookmaker="contrarian",
                model="contrarian",
                analysis_type="prop",
                sport=prop_item.get("sport"),
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=prop_item.get("player_name", "Unknown Player"),
                market_key=prop_item.get("market_key"),
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
                recommended_odds=-110,
            )

        except Exception as e:
            logger.error(f"Error analyzing contrarian prop odds: {e}", exc_info=True)
            return None


class HotColdModel(BaseAnalysisModel):
    """Hot/Cold model: Track recent form and momentum"""

    def __init__(self, dynamodb_table=None):
        """Initialize with optional DynamoDB table for querying recent games"""
        self.table = dynamodb_table
        if not self.table:
            import os

            import boto3

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)
        
        self.player_analytics = PlayerAnalytics()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """
        Analyze based on recent team performance
        - Query last 5-10 games for each team
        - Calculate win/loss streaks
        - Weight recent games more heavily
        """
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        sport = game_info.get("sport")

        # Get recent performance for both teams
        home_record = self._get_recent_record(home_team, sport, lookback=10)
        away_record = self._get_recent_record(away_team, sport, lookback=10)

        # Calculate form scores (0-1)
        home_form = self._calculate_form_score(home_record)
        away_form = self._calculate_form_score(away_record)

        # Determine prediction based on form differential
        form_diff = home_form - away_form

        # Get spread for context
        spread = self._get_current_spread(odds_items)

        if abs(form_diff) > 0.3:
            # Strong form differential
            confidence = 0.75
            if form_diff > 0:
                prediction = f"{home_team} {spread:+.1f}"
                reasoning = f"Strong home form: {home_record['wins']}-{home_record['losses']} last {home_record['games']} games. Away: {away_record['wins']}-{away_record['losses']}."
            else:
                prediction = f"{away_team} {-spread:+.1f}"
                reasoning = f"Strong away form: {away_record['wins']}-{away_record['losses']} last {away_record['games']} games. Home: {home_record['wins']}-{home_record['losses']}."
        elif abs(form_diff) > 0.15:
            # Moderate form differential
            confidence = 0.65
            if form_diff > 0:
                prediction = f"{home_team} {spread:+.1f}"
                reasoning = f"Home team trending up ({home_record['wins']}-{home_record['losses']}), away trending down ({away_record['wins']}-{away_record['losses']})."
            else:
                prediction = f"{away_team} {-spread:+.1f}"
                reasoning = f"Away team trending up ({away_record['wins']}-{away_record['losses']}), home trending down ({home_record['wins']}-{home_record['losses']})."
        else:
            # Similar form, slight edge to home
            confidence = 0.55
            prediction = f"{home_team} {spread:+.1f}"
            reasoning = f"Similar recent form. Home: {home_record['wins']}-{home_record['losses']}, Away: {away_record['wins']}-{away_record['losses']}. Slight home edge."

        return AnalysisResult(
            game_id=game_id,
            model="hot_cold",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def _get_recent_record(
        self, team: str, sport: str, lookback: int = 10
    ) -> Dict[str, int]:
        """
        Query recent games for a team
        Returns wins, losses, and total games
        """
        try:
            # Query for recent games where this team played
            response = self.table.query(
                IndexName="AnalysisTimeGSI",
                KeyConditionExpression="analysis_time_pk = :pk",
                FilterExpression="(home_team = :team OR away_team = :team) AND attribute_exists(analysis_correct)",
                ExpressionAttributeValues={
                    ":pk": f"ANALYSIS#{sport}#all#all#game",
                    ":team": team,
                },
                Limit=lookback,
                ScanIndexForward=False,  # Most recent first
            )

            items = response.get("Items", [])

            if not items:
                # No data available, return neutral record
                return {"wins": 5, "losses": 5, "games": 10}

            wins = 0
            losses = 0

            for item in items:
                home_team = item.get("home_team")
                prediction = item.get("prediction", "")
                correct = item.get("analysis_correct", False)

                # Determine if this team won
                if home_team == team:
                    # Team was home
                    team_won = correct if team in prediction else not correct
                else:
                    # Team was away
                    team_won = correct if team in prediction else not correct

                if team_won:
                    wins += 1
                else:
                    losses += 1

            return {"wins": wins, "losses": losses, "games": wins + losses}

        except Exception as e:
            logger.error(f"Error querying recent record: {e}", exc_info=True)
            # Return neutral record on error
            return {"wins": 5, "losses": 5, "games": 10}

    def _calculate_form_score(self, record: Dict[str, int]) -> float:
        """
        Calculate form score (0-1) based on recent record
        Weight recent games more heavily
        """
        games = record["games"]
        if games == 0:
            return 0.5  # Neutral

        win_pct = record["wins"] / games

        # Boost for winning streaks
        if record["wins"] >= games * 0.7:
            # Hot team (70%+ wins)
            return min(win_pct * 1.2, 1.0)
        elif record["losses"] >= games * 0.7:
            # Cold team (70%+ losses)
            return max(win_pct * 0.8, 0.0)
        else:
            return win_pct

    def _get_current_spread(self, odds_items: List[Dict]) -> float:
        """Get current spread from odds items"""
        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    return float(item["outcomes"][0].get("point", 0))
        return 0.0

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """
        Analyze prop based on player's recent performance
        Queries last 5-10 games for player stats
        """
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            player_name = prop_item.get("player_name", "Unknown Player")
            sport = prop_item.get("sport")
            market_key = prop_item.get("market_key", "")
            line = prop_item.get("point", 0)

            # Get recent player performance
            recent_stats = self._get_recent_player_stats(player_name, sport, market_key)

            if not recent_stats or recent_stats["games"] == 0:
                # No data available, return neutral prediction
                return AnalysisResult(
                    game_id=prop_item.get("event_id", "unknown"),
                    bookmaker="hot_cold",
                    model="hot_cold",
                    analysis_type="prop",
                    sport=sport,
                    home_team=prop_item.get("home_team"),
                    away_team=prop_item.get("away_team"),
                    commence_time=prop_item.get("commence_time"),
                    player_name=player_name,
                    market_key=market_key,
                    prediction=f"Over {line}",
                    confidence=0.55,
                    reasoning=f"Insufficient data for {player_name}. Neutral prediction.",
                    recommended_odds=-110,
                )

            # Calculate if player is hot or cold
            avg_stat = recent_stats["average"]
            over_rate = recent_stats["over_count"] / recent_stats["games"]
            avg_per = recent_stats.get("avg_per")
            avg_efficiency = recent_stats.get("avg_efficiency")

            # Convert line to float for comparison
            line_float = float(line)
            
            # Get enhanced analytics
            home_away_splits = self.player_analytics.get_home_away_splits(player_name, sport)
            matchup_history = self.player_analytics.get_matchup_history(
                player_name, 
                prop_item.get('home_team', ''),  # Opponent team
                sport
            )
            form_trend = self.player_analytics.get_recent_form_trend(player_name, sport)
            
            # Adjust confidence based on efficiency metrics
            efficiency_boost = 0.0
            efficiency_context = ""
            
            if sport == "basketball_nba" and avg_per is not None:
                # League average PER is 15.0
                if avg_per > 20:
                    efficiency_boost = 0.05
                    efficiency_context = f" High efficiency (PER: {avg_per:.1f})."
                elif avg_per < 10:
                    efficiency_boost = -0.05
                    efficiency_context = f" Low efficiency (PER: {avg_per:.1f})."
            
            elif sport == "americanfootball_nfl" and avg_efficiency is not None:
                # QB rating avg ~90, RB/WR efficiency avg ~8-10
                if avg_efficiency > 100 or avg_efficiency > 12:
                    efficiency_boost = 0.05
                    efficiency_context = f" High efficiency ({avg_efficiency:.1f})."
                elif avg_efficiency < 70 or avg_efficiency < 6:
                    efficiency_boost = -0.05
                    efficiency_context = f" Low efficiency ({avg_efficiency:.1f})."
            
            # Adjust for home/away splits
            split_boost = 0.0
            split_context = ""
            if home_away_splits and abs(home_away_splits.get('split_difference', 0)) > 15:
                is_home_game = prop_item.get('is_home', True)
                split_diff = home_away_splits['split_difference']
                if (is_home_game and split_diff > 0) or (not is_home_game and split_diff < 0):
                    split_boost = 0.03
                    split_context = f" Favorable home/away split."
                else:
                    split_boost = -0.03
                    split_context = f" Unfavorable home/away split."
            
            # Adjust for matchup history
            matchup_boost = 0.0
            matchup_context = ""
            if matchup_history.get('games', 0) >= 3:
                matchup_avg = matchup_history['avg_stats'].get(self._map_market_to_stat(market_key), 0)
                if matchup_avg > line_float * 1.15:
                    matchup_boost = 0.03
                    matchup_context = f" Strong vs this opponent ({matchup_avg:.1f} avg)."
                elif matchup_avg < line_float * 0.85:
                    matchup_boost = -0.03
                    matchup_context = f" Struggles vs this opponent ({matchup_avg:.1f} avg)."
            
            # Adjust for form trend
            trend_boost = 0.0
            trend_context = ""
            if form_trend.get('direction') == 1:
                trend_boost = 0.02
                trend_context = f" Trending up ({form_trend.get('pct_change', 0):+.1f}%)."
            elif form_trend.get('direction') == -1:
                trend_boost = -0.02
                trend_context = f" Trending down ({form_trend.get('pct_change', 0):+.1f}%)."
            
            # Combine all boosts
            total_boost = efficiency_boost + split_boost + matchup_boost + trend_boost
            context = efficiency_context + split_context + matchup_context + trend_context
            
            # Determine prediction based on recent performance
            if avg_stat > line_float * 1.1 and over_rate > 0.7:
                # Hot player, well above line
                confidence = min(0.75 + total_boost, 0.85)
                prediction = f"Over {line}"
                reasoning = f"{player_name} is HOT: Averaging {avg_stat:.1f} in last {recent_stats['games']} games, well above the {line} line. Hit over {int(over_rate*100)}% of the time.{context}"
            elif avg_stat > line_float and over_rate > 0.6:
                # Trending over
                confidence = min(0.65 + total_boost, 0.75)
                prediction = f"Over {line}"
                reasoning = f"{player_name} playing well: Averaging {avg_stat:.1f} with {int(over_rate*100)}% over rate in last {recent_stats['games']} games.{context}"
            elif avg_stat < line_float * 0.9 and over_rate < 0.3:
                # Cold player, well below line
                confidence = min(0.75 + abs(total_boost), 0.85)
                prediction = f"Under {line}"
                reasoning = f"{player_name} is COLD: Averaging {avg_stat:.1f} in last {recent_stats['games']} games, well below the {line} line. Hit under {int((1-over_rate)*100)}% of the time.{context}"
            elif avg_stat < line_float and over_rate < 0.4:
                # Trending under
                confidence = 0.65
                prediction = f"Under {line}"
                reasoning = f"{player_name} struggling: Averaging {avg_stat:.1f} with {int((1-over_rate)*100)}% under rate in last {recent_stats['games']} games"
            else:
                # Close to line, slight edge based on recent trend
                confidence = 0.55
                if avg_stat > line:
                    prediction = f"Over {line}"
                    reasoning = f"{player_name} slightly above line: {avg_stat:.1f} average in last {recent_stats['games']} games"
                else:
                    prediction = f"Under {line}"
                    reasoning = f"{player_name} slightly below line: {avg_stat:.1f} average in last {recent_stats['games']} games"

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                bookmaker="hot_cold",
                model="hot_cold",
                analysis_type="prop",
                sport=sport,
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=player_name,
                market_key=market_key,
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
                recommended_odds=-110,
            )

        except Exception as e:
            logger.error(f"Error analyzing hot/cold prop odds: {e}", exc_info=True)
            return None

    def _get_recent_player_stats(
        self, player_name: str, sport: str, market_key: str, lookback: int = 10
    ) -> Dict[str, Any]:
        """
        Query recent player stats
        Returns average, games played, over/under count, and PER
        Weights recent games by minutes played for importance
        """
        try:
            # Normalize player name to match storage format
            normalized_name = player_name.lower().replace(" ", "_")
            pk = f"PLAYER_STATS#{sport}#{normalized_name}"

            # Query recent stats
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                Limit=lookback,
                ScanIndexForward=False,  # Most recent first
            )

            items = response.get("Items", [])

            if not items:
                return {"games": 0, "average": 0, "over_count": 0, "avg_per": None}

            # Extract stat based on market_key
            stat_field = self._map_market_to_stat(market_key)
            weighted_sum = 0.0
            total_weight = 0.0
            games_count = 0
            per_values = []

            for item in items:
                stats = item.get("stats", {})
                if stat_field in stats:
                    try:
                        value = float(stats[stat_field])
                        minutes = float(stats.get("MIN", 20))  # Default 20 if missing

                        # Weight by minutes played (more minutes = more reliable)
                        # 30+ minutes = full weight, <10 minutes = 0.3 weight
                        weight = min(minutes / 30.0, 1.0) if minutes > 0 else 0.3

                        weighted_sum += value * weight
                        total_weight += weight
                        games_count += 1
                        
                        # Collect PER values for NBA
                        if sport == "basketball_nba" and "per" in stats:
                            per_values.append(float(stats["per"]))
                        
                        # Collect efficiency values for NFL
                        if sport == "americanfootball_nfl" and "efficiency" in stats:
                            per_values.append(float(stats["efficiency"]))
                    except (ValueError, TypeError):
                        continue

            if games_count == 0 or total_weight == 0:
                return {"games": 0, "average": 0, "over_count": 0, "avg_per": None}

            weighted_avg = weighted_sum / total_weight
            avg_per = sum(per_values) / len(per_values) if per_values else None

            return {
                "games": games_count, 
                "average": weighted_avg, 
                "over_count": 0,
                "avg_per": avg_per if sport == "basketball_nba" else None,
                "avg_efficiency": avg_per if sport == "americanfootball_nfl" else None
            }

        except Exception as e:
            logger.error(f"Error querying player stats: {e}", exc_info=True)
            return {"games": 0, "average": 0, "over_count": 0, "avg_per": None, "avg_efficiency": None}

    def _map_market_to_stat(self, market_key: str) -> str:
        """Map prop market key to player stat field"""
        mapping = {
            "player_points": "PTS",
            "player_rebounds": "REB",
            "player_assists": "AST",
            "player_threes": "3PM",
            "player_blocks": "BLK",
            "player_steals": "STL",
            "player_turnovers": "TO",
            "player_points_rebounds_assists": "PTS+REB+AST",
        }
        return mapping.get(market_key, "PTS")


class RestScheduleModel(BaseAnalysisModel):
    """Model that analyzes rest days, back-to-back games, and travel fatigue"""

    def __init__(self, dynamodb_table=None):
        """Initialize with optional DynamoDB table"""
        self.table = dynamodb_table
        if not self.table:
            import os

            import boto3

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)
        
        self.fatigue_calculator = TravelFatigueCalculator()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """Analyze game based on rest and schedule factors with comprehensive fatigue"""
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        game_date = game_info.get("commence_time")

        # Use comprehensive fatigue calculator
        try:
            home_fatigue = self.fatigue_calculator.calculate_fatigue_score(home_team, sport, game_date)
            away_fatigue = self.fatigue_calculator.calculate_fatigue_score(away_team, sport, game_date)
            
            # Lower fatigue score = better (inverted for advantage calculation)
            home_advantage = (100 - home_fatigue['fatigue_score']) - (100 - away_fatigue['fatigue_score'])
            home_advantage = home_advantage / 20  # Scale to reasonable range
            
            confidence = 0.5 + (abs(home_advantage) * 0.05)
            confidence = max(0.3, min(0.85, confidence))
            
            pick = home_team if home_advantage > 0 else away_team
            
            # Build detailed reasoning
            reasons = []
            if home_fatigue['back_to_back']:
                reasons.append(f"{home_team} on back-to-back")
            if away_fatigue['back_to_back']:
                reasons.append(f"{away_team} on back-to-back")
            
            if home_fatigue['total_miles'] > 1000:
                reasons.append(f"{home_team} traveled {home_fatigue['total_miles']:.0f} miles")
            if away_fatigue['total_miles'] > 1000:
                reasons.append(f"{away_team} traveled {away_fatigue['total_miles']:.0f} miles")
            
            if not reasons:
                reasons.append(f"{home_team} {home_fatigue['days_rest']}d rest vs {away_team} {away_fatigue['days_rest']}d rest")
            
            reasoning = "Fatigue advantage: " + ", ".join(reasons) + f". Impact: {home_fatigue['impact']} vs {away_fatigue['impact']}."
            
        except Exception as e:
            logger.error(f"Error calculating fatigue: {e}")
            # Fallback to simple rest calculation
            home_rest = self._get_rest_score(sport, home_team.lower().replace(" ", "_"), game_date, is_home=True)
            away_rest = self._get_rest_score(sport, away_team.lower().replace(" ", "_"), game_date, is_home=False)
            
            rest_advantage = home_rest - away_rest
            confidence = 0.5 + (rest_advantage * 0.05)
            confidence = max(0.3, min(0.9, confidence))
            
            pick = home_team if rest_advantage > 0 else away_team
            reasoning = f"Rest advantage: {home_team} ({home_rest:.1f}) vs {away_team} ({away_rest:.1f})"

        return AnalysisResult(
            game_id=game_id,
            model="rest_schedule",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_date,
            prediction=pick,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop based on team rest situation"""
        sport = prop_item.get("sport")
        player_name = prop_item.get("player_name", "").lower().replace(" ", "_")
        game_date = prop_item.get("commence_time")

        # Get team from player stats
        team = self._get_player_team(sport, player_name)
        if not team:
            return None

        rest_score = self._get_rest_score(sport, team, game_date, is_home=True)

        confidence = 0.5 + (rest_score * 0.03)
        confidence = max(0.3, min(0.8, confidence))

        pick = "over" if rest_score > 1 else "under"
        reasoning = f"Team rest score: {rest_score:.1f}"

        return AnalysisResult(
            game_id=prop_item.get("game_id"),
            model="rest_schedule",
            analysis_type="prop",
            sport=sport,
            player_name=prop_item.get("player_name"),
            market_key=prop_item.get("market_key"),
            commence_time=game_date,
            prediction=pick,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def _get_rest_score(
        self, sport: str, team: str, game_date: str, is_home: bool
    ) -> float:
        """Calculate rest score for a team"""
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk AND sk <= :date",
                ExpressionAttributeValues={
                    ":pk": f"SCHEDULE#{sport}#{team}",
                    ":date": game_date,
                },
                ScanIndexForward=False,
                Limit=2,
            )

            items = response.get("Items", [])
            if not items:
                return 0.0

            # Current game
            current_game = items[0]
            rest_days = current_game.get("rest_days", 2)

            score = 0.0

            # Rest days factor
            if rest_days >= 3:
                score += 3.0
            elif rest_days == 2:
                score += 1.5
            elif rest_days == 1:
                score += 0.5
            elif rest_days == 0:
                score -= 3.0  # Back-to-back

            # Home advantage
            if is_home:
                score += 1.0
            else:
                score -= 0.5

            return score

        except Exception as e:
            logger.error(f"Error getting rest score: {e}", exc_info=True)
            return 0.0

    def _get_player_team(self, sport: str, player_name: str) -> Optional[str]:
        """Get team for a player from recent stats"""
        try:
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={
                    ":pk": f"PLAYER_STATS#{sport}#{player_name}"
                },
                ScanIndexForward=False,
                Limit=1,
            )

            items = response.get("Items", [])
            if items:
                return items[0].get("team", "").lower().replace(" ", "_")
            return None

        except Exception as e:
            logger.error(f"Error getting player team: {e}", exc_info=True)
            return None


class MatchupModel(BaseAnalysisModel):
    """Model that analyzes head-to-head history and style matchups with weather"""

    def __init__(self, dynamodb_table=None):
        """Initialize with optional DynamoDB table"""
        self.table = dynamodb_table
        if not self.table:
            import os

            import boto3

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)
        
        self.weather_collector = WeatherCollector()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """Analyze game based on matchup history and team styles"""
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")

        # Get head-to-head history
        h2h_advantage = self._get_h2h_advantage(sport, home_team, away_team)

        # Get style matchup
        style_advantage = self._get_style_matchup(sport, home_team, away_team)

        # Combined advantage
        total_advantage = (h2h_advantage * 0.6) + (style_advantage * 0.4)

        # Calculate confidence
        confidence = 0.5 + (abs(total_advantage) * 0.1)
        confidence = max(0.3, min(0.85, confidence))
        
        # Check weather for outdoor sports
        weather_context = ""
        try:
            if sport in ['americanfootball_nfl', 'baseball_mlb', 'soccer_epl']:
                # Try to get stored weather data
                weather_response = self.table.get_item(
                    Key={"pk": f"WEATHER#{game_id}", "sk": "latest"}
                )
                weather_data = weather_response.get("Item")
                
                if weather_data and weather_data.get("impact") in ["high", "moderate"]:
                    impact = weather_data.get("impact")
                    wind = weather_data.get("wind_mph", 0)
                    temp = weather_data.get("temp_f", 70)
                    precip = weather_data.get("precip_in", 0)
                    
                    conditions = []
                    if wind > 15:
                        conditions.append(f"{wind}mph wind")
                    if temp < 32:
                        conditions.append(f"{temp}°F")
                    if precip > 0.2:
                        conditions.append(f"{precip}\" rain")
                    
                    if conditions:
                        weather_context = f" Weather impact ({impact}): {', '.join(conditions)}."
                        # Adjust confidence slightly for weather uncertainty
                        confidence = max(confidence - 0.05, 0.3)
        except Exception as e:
            logger.error(f"Error getting weather data: {e}")

        # Make prediction
        pick = home_team if total_advantage > 0 else away_team
        
        # Create human-readable reasoning
        favored_team = home_team if total_advantage > 0 else away_team
        
        reasons = []
        if abs(h2h_advantage) > 0.5:
            reasons.append(f"head-to-head record favors {home_team if h2h_advantage > 0 else away_team}")
        
        if abs(style_advantage) > 0.5:
            reasons.append(f"offensive/defensive matchup favors {home_team if style_advantage > 0 else away_team}")
        
        if not reasons:
            reasoning = f"Slight edge to {favored_team}.{weather_context}"
        else:
            reasoning = ", ".join(reasons).capitalize() + f".{weather_context}"

        return AnalysisResult(
            game_id=game_id,
            model="matchup",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=pick,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop based on player matchup history"""
        try:
            player = prop_item.get("player_name")
            if not player:
                return None

            sport = prop_item.get("sport")

            # Get opponent from game info
            game_id = prop_item.get("event_id")
            game_response = self.table.get_item(
                Key={"pk": f"GAME#{game_id}", "sk": "LATEST"}
            )
            game_item = game_response.get("Item", {})
            home_team = game_item.get("home_team", "")
            away_team = game_item.get("away_team", "")

            # Determine opponent (player's team vs opponent)
            player_team = prop_item.get("team", "")
            opponent = away_team if player_team == home_team else home_team

            # Get player's historical stats vs this opponent
            vs_opponent_avg = self._get_player_vs_opponent_avg(
                sport, player, opponent, prop_item.get("market_key")
            )

            if vs_opponent_avg is None:
                return None

            # Compare to prop line
            prop_line = float(prop_item.get("point", 0))
            diff = vs_opponent_avg - prop_line

            # Calculate confidence based on difference
            confidence = 0.5 + min(abs(diff) * 0.05, 0.25)

            if diff > 2:
                prediction = f"Over {prop_line}"
                reasoning = f"Averages {vs_opponent_avg:.1f} vs {opponent}"
            elif diff < -2:
                prediction = f"Under {prop_line}"
                reasoning = f"Averages {vs_opponent_avg:.1f} vs {opponent}"
            else:
                return None  # Not confident enough

            return AnalysisResult(
                game_id=game_id,
                model="matchup",
                analysis_type="prop",
                sport=sport,
                home_team=home_team,
                away_team=away_team,
                commence_time=prop_item.get("commence_time"),  # Get from prop_item, not game_item
                prediction=prediction,
                confidence=confidence,
                reasoning=reasoning,
                recommended_odds=-110,
            )
        except Exception as e:
            logger.error(f"Error analyzing prop matchup: {e}", exc_info=True)
            return None

    def _get_h2h_advantage(self, sport: str, home_team: str, away_team: str) -> float:
        """Get head-to-head advantage from historical games"""
        try:
            # Normalize team names for H2H query
            home_normalized = home_team.lower().replace(" ", "_")
            away_normalized = away_team.lower().replace(" ", "_")

            # Sort teams alphabetically for consistent H2H key
            teams_sorted = sorted([home_normalized, away_normalized])
            h2h_pk = f"H2H#{sport}#{teams_sorted[0]}#{teams_sorted[1]}"

            # Query H2H index for recent games
            response = self.table.query(
                IndexName="H2HIndex",
                KeyConditionExpression="h2h_pk = :pk",
                ExpressionAttributeValues={":pk": h2h_pk},
                ScanIndexForward=False,  # Most recent first
                Limit=10,
            )

            home_wins = 0
            away_wins = 0
            total_games = 0

            for item in response.get("Items", []):
                winner = item.get("winner", "")
                if winner == home_team:
                    home_wins += 1
                elif winner == away_team:
                    away_wins += 1
                total_games += 1

            if total_games == 0:
                return 0.0

            # Calculate advantage (-2 to +2 scale)
            win_rate = home_wins / total_games
            return (win_rate - 0.5) * 4

        except Exception as e:
            logger.error(f"Error getting H2H advantage: {e}", exc_info=True)
            return 0.0

    def _get_style_matchup(self, sport: str, home_team: str, away_team: str) -> float:
        """Analyze style matchup between teams"""
        try:
            home_stats = self._get_team_stats(sport, home_team)
            away_stats = self._get_team_stats(sport, away_team)

            if not home_stats or not away_stats:
                return 0.0

            # Compare offensive vs defensive ratings
            home_offense = home_stats.get("points_per_game", 0)
            home_defense = home_stats.get("points_allowed_per_game", 999)
            away_offense = away_stats.get("points_per_game", 0)
            away_defense = away_stats.get("points_allowed_per_game", 999)

            # Home advantage calculation:
            # Positive if home offense beats away defense AND home defense beats away offense
            # Home offense vs away defense (higher offense vs lower defense = advantage)
            offense_matchup = home_offense - away_defense
            # Home defense vs away offense (lower defense vs higher offense = advantage)
            defense_matchup = away_offense - home_defense

            # Combine (both should be positive for home advantage)
            return (offense_matchup + defense_matchup) / 20

        except Exception as e:
            logger.error(f"Error getting style matchup: {e}", exc_info=True)
            return 0.0

    def _get_team_stats(self, sport: str, team: str) -> Optional[Dict]:
        """Get recent team statistics"""
        try:
            team_key = team.lower().replace(" ", "_")
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": f"TEAM_STATS#{sport}#{team_key}"},
                ScanIndexForward=False,
                Limit=1,
            )

            items = response.get("Items", [])
            return items[0] if items else None

        except Exception as e:
            logger.error(f"Error getting team stats: {e}", exc_info=True)
            return None

    def _get_player_vs_opponent_avg(
        self, sport: str, player_name: str, opponent: str, stat_key: str
    ) -> Optional[float]:
        """Get player's average stat vs specific opponent"""
        try:
            normalized_player = player_name.lower().replace(" ", "_")
            normalized_opponent = opponent.lower().replace(" ", "_")

            # Query all player stats, then filter by opponent
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={
                    ":pk": f"PLAYER_STATS#{sport}#{normalized_player}",
                },
                ScanIndexForward=False,
                Limit=20,  # Get more, filter to last 5 vs opponent
            )

            items = response.get("Items", [])
            if not items:
                return None

            # Filter for opponent in SK
            opponent_games = [
                item
                for item in items
                if normalized_opponent in item.get("sk", "").lower()
            ][
                :5
            ]  # Last 5 vs this opponent

            if not opponent_games:
                return None

            # Map prop key to stat name
            stat_map = {
                "player_points": "PTS",
                "player_rebounds": "REB",
                "player_assists": "AST",
                "player_threes": "3PM",
            }
            stat_name = stat_map.get(stat_key, "PTS")

            # Calculate average
            total = 0
            count = 0
            for item in opponent_games:
                stats = item.get("stats", {})
                stat_value = stats.get(stat_name)
                if stat_value:
                    total += float(stat_value)
                    count += 1

            return total / count if count > 0 else None

        except Exception as e:
            logger.error(f"Error getting player vs opponent avg: {e}", exc_info=True)
            return None


class InjuryAwareModel(BaseAnalysisModel):
    """Injury-Aware model: Adjust predictions based on player injuries"""

    def __init__(self, dynamodb_table=None):
        self.table = dynamodb_table
        if not self.table:
            import os

            import boto3

            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        """Analyze game odds considering injury impact"""
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        sport = game_info.get("sport")

        # Get injuries for both teams
        home_injuries = self._get_team_injuries(home_team, sport)
        away_injuries = self._get_team_injuries(away_team, sport)

        # Calculate injury impact scores
        home_impact = self._calculate_injury_impact(home_injuries)
        away_impact = self._calculate_injury_impact(away_injuries)

        # Determine prediction based on injury differential
        impact_diff = away_impact - home_impact  # Higher away impact favors home
        spread = self._get_current_spread(odds_items)

        if abs(impact_diff) > 0.3:
            confidence = 0.75
            if impact_diff > 0:
                prediction = f"{home_team} {spread:+.1f}"
                reasoning = f"{away_team} has {len(away_injuries)} key injuries. {home_team} healthier with {len(home_injuries)} injuries."
            else:
                prediction = f"{away_team} {-spread:+.1f}"
                reasoning = f"{home_team} has {len(home_injuries)} key injuries. {away_team} healthier with {len(away_injuries)} injuries."
        elif abs(impact_diff) > 0.15:
            confidence = 0.65
            if impact_diff > 0:
                prediction = f"{home_team} {spread:+.1f}"
                reasoning = f"{away_team} dealing with injuries ({len(away_injuries)} out). {home_team} advantage."
            else:
                prediction = f"{away_team} {-spread:+.1f}"
                reasoning = f"{home_team} dealing with injuries ({len(home_injuries)} out). {away_team} advantage."
        else:
            confidence = 0.55
            prediction = f"{home_team} {spread:+.1f}"
            reasoning = f"Both teams relatively healthy. {home_team}: {len(home_injuries)} injuries, {away_team}: {len(away_injuries)} injuries."

        return AnalysisResult(
            game_id=game_id,
            model="injury_aware",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_info.get("commence_time"),
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop considering player injury status"""
        try:
            player_name = prop_item.get("player_name", "Unknown Player")
            sport = prop_item.get("sport")
            market_key = prop_item.get("market_key", "")
            line = prop_item.get("point", 0)

            # Check if player is injured
            player_injury = self._get_player_injury_status(player_name, sport)

            if player_injury and player_injury.get("status") in ["Out", "Doubtful"]:
                return AnalysisResult(
                    game_id=prop_item.get("event_id", "unknown"),
                    bookmaker="injury_aware",
                    model="injury_aware",
                    analysis_type="prop",
                    sport=sport,
                    home_team=prop_item.get("home_team"),
                    away_team=prop_item.get("away_team"),
                    commence_time=prop_item.get("commence_time"),
                    player_name=player_name,
                    market_key=market_key,
                    prediction="AVOID",
                    confidence=0.9,
                    reasoning=f"{player_name} listed as {player_injury['status']} ({player_injury.get('injury_type', 'injury')}). Avoid this prop.",
                    recommended_odds=-110,
                )

            # Player is healthy or questionable
            confidence = 0.6 if player_injury else 0.55
            status_note = (
                f" (listed as {player_injury['status']})" if player_injury else ""
            )

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
                bookmaker="injury_aware",
                model="injury_aware",
                analysis_type="prop",
                sport=sport,
                home_team=prop_item.get("home_team"),
                away_team=prop_item.get("away_team"),
                commence_time=prop_item.get("commence_time"),
                player_name=player_name,
                market_key=market_key,
                prediction=f"Over {line}",
                confidence=confidence,
                reasoning=f"{player_name} healthy{status_note}. Monitor injury reports before game.",
                recommended_odds=-110,
            )

        except Exception as e:
            logger.error(f"Error analyzing injury-aware prop: {e}", exc_info=True)
            return None

    def _get_team_injuries(self, team: str, sport: str) -> List[Dict]:
        """Get current injuries for a team"""
        try:
            # Map team name to ESPN team ID (simplified - would need full mapping)
            team_id = self._get_team_id(team, sport)
            if not team_id:
                return []

            pk = f"INJURIES#{sport}#{team_id}"
            response = self.table.query(
                KeyConditionExpression="pk = :pk",
                ExpressionAttributeValues={":pk": pk},
                Limit=1,
                ScanIndexForward=False,
            )

            items = response.get("Items", [])
            if items:
                return [
                    inj
                    for inj in items[0].get("injuries", [])
                    if inj.get("status") == "Out"
                ]
            return []

        except Exception as e:
            logger.error(f"Error getting team injuries: {e}", exc_info=True)
            return []

    def _get_player_injury_status(self, player_name: str, sport: str) -> Dict:
        """Check if a specific player is injured"""
        try:
            # Normalize player name to match storage format
            normalized_name = player_name.lower().replace(" ", "_")
            pk = f"PLAYER_INJURY#{sport}#{normalized_name}"

            response = self.table.query(
                KeyConditionExpression="pk = :pk AND sk = :sk",
                ExpressionAttributeValues={":pk": pk, ":sk": "LATEST"},
                Limit=1,
            )

            items = response.get("Items", [])
            if items:
                item = items[0]
                return {
                    "status": item.get("status"),
                    "injury_type": item.get("injury_type"),
                    "return_date": item.get("return_date"),
                }

            return None

        except Exception as e:
            logger.error(f"Error checking player injury status: {e}", exc_info=True)
            return None

    def _calculate_injury_impact(self, injuries: List[Dict]) -> float:
        """Calculate overall injury impact (0-1 scale) weighted by player value"""
        if not injuries:
            return 0.0

        total_impact = 0.0
        for injury in injuries:
            # Get player value metrics (convert Decimal to float)
            usage_rate = float(injury.get("usage_rate", 20))  # % of team possessions
            per = float(injury.get("per", 15))  # Player Efficiency Rating
            win_shares = float(injury.get("win_shares", 0))  # Contribution to wins
            avg_minutes = float(injury.get("avg_minutes", 0))
            
            # Calculate player value score (0-1 scale)
            # Usage rate: 20% = average, 30%+ = star
            usage_score = min(usage_rate / 35, 1.0)
            
            # PER: 15 = average, 25+ = elite
            per_score = min(max(per - 10, 0) / 20, 1.0)
            
            # Win shares: 0.1 per game = star level
            ws_score = min(win_shares / 10, 1.0)
            
            # Minutes: 35+ = starter
            minutes_score = min(avg_minutes / 35, 1.0)
            
            # Weighted average of all metrics
            player_value = (usage_score * 0.3 + per_score * 0.3 + 
                          ws_score * 0.2 + minutes_score * 0.2)
            
            # Adjust by injury severity
            status = injury.get("status", "Out")
            if status == "Out":
                severity = 1.0
            elif status == "Doubtful":
                severity = 0.8
            elif status == "Questionable":
                severity = 0.4
            else:
                severity = 0.2
            
            total_impact += player_value * severity

        # Cap at 1.0 (losing multiple stars)
        return min(total_impact, 1.0)

    def _get_current_spread(self, odds_items: List[Dict]) -> float:
        """Get current spread from odds items"""
        for item in odds_items:
            if "spreads" in item.get("sk", "") and "outcomes" in item:
                if len(item["outcomes"]) >= 2:
                    return float(item["outcomes"][0].get("point", 0))
        return 0.0

    def _get_team_id(self, team_name: str, sport: str) -> str:
        """Map team name to ESPN team ID"""
        team_mapping = {
            "basketball_nba": {
                "Atlanta Hawks": "1",
                "Boston Celtics": "2",
                "Brooklyn Nets": "17",
                "Charlotte Hornets": "30",
                "Chicago Bulls": "4",
                "Cleveland Cavaliers": "5",
                "Dallas Mavericks": "6",
                "Denver Nuggets": "7",
                "Detroit Pistons": "8",
                "Golden State Warriors": "9",
                "Houston Rockets": "10",
                "Indiana Pacers": "11",
                "LA Clippers": "12",
                "Los Angeles Lakers": "13",
                "Memphis Grizzlies": "29",
                "Miami Heat": "14",
                "Milwaukee Bucks": "15",
                "Minnesota Timberwolves": "16",
                "New Orleans Pelicans": "3",
                "New York Knicks": "18",
                "Oklahoma City Thunder": "25",
                "Orlando Magic": "19",
                "Philadelphia 76ers": "20",
                "Phoenix Suns": "21",
                "Portland Trail Blazers": "22",
                "Sacramento Kings": "23",
                "San Antonio Spurs": "24",
                "Toronto Raptors": "28",
                "Utah Jazz": "26",
                "Washington Wizards": "27",
            },
            "americanfootball_nfl": {
                "Arizona Cardinals": "22",
                "Atlanta Falcons": "1",
                "Baltimore Ravens": "33",
                "Buffalo Bills": "2",
                "Carolina Panthers": "29",
                "Chicago Bears": "3",
                "Cincinnati Bengals": "4",
                "Cleveland Browns": "5",
                "Dallas Cowboys": "6",
                "Denver Broncos": "7",
                "Detroit Lions": "8",
                "Green Bay Packers": "9",
                "Houston Texans": "34",
                "Indianapolis Colts": "11",
                "Jacksonville Jaguars": "30",
                "Kansas City Chiefs": "12",
                "Las Vegas Raiders": "13",
                "Los Angeles Chargers": "24",
                "Los Angeles Rams": "14",
                "Miami Dolphins": "15",
                "Minnesota Vikings": "16",
                "New England Patriots": "17",
                "New Orleans Saints": "18",
                "New York Giants": "19",
                "New York Jets": "20",
                "Philadelphia Eagles": "21",
                "Pittsburgh Steelers": "23",
                "San Francisco 49ers": "25",
                "Seattle Seahawks": "26",
                "Tampa Bay Buccaneers": "27",
                "Tennessee Titans": "10",
                "Washington Commanders": "28",
            },
            "baseball_mlb": {
                "Arizona Diamondbacks": "29",
                "Athletics": "11",
                "Atlanta Braves": "15",
                "Baltimore Orioles": "1",
                "Boston Red Sox": "2",
                "Chicago Cubs": "16",
                "Chicago White Sox": "4",
                "Cincinnati Reds": "17",
                "Cleveland Guardians": "5",
                "Colorado Rockies": "27",
                "Detroit Tigers": "6",
                "Houston Astros": "18",
                "Kansas City Royals": "7",
                "Los Angeles Angels": "3",
                "Los Angeles Dodgers": "19",
                "Miami Marlins": "28",
                "Milwaukee Brewers": "8",
                "Minnesota Twins": "9",
                "New York Mets": "21",
                "New York Yankees": "10",
                "Philadelphia Phillies": "22",
                "Pittsburgh Pirates": "23",
                "San Diego Padres": "25",
                "San Francisco Giants": "26",
                "Seattle Mariners": "12",
                "St. Louis Cardinals": "24",
                "Tampa Bay Rays": "30",
                "Texas Rangers": "13",
                "Toronto Blue Jays": "14",
                "Washington Nationals": "20",
            },
            "icehockey_nhl": {
                "Anaheim Ducks": "25",
                "Boston Bruins": "1",
                "Buffalo Sabres": "2",
                "Calgary Flames": "3",
                "Carolina Hurricanes": "7",
                "Chicago Blackhawks": "4",
                "Colorado Avalanche": "17",
                "Columbus Blue Jackets": "29",
                "Dallas Stars": "9",
                "Detroit Red Wings": "5",
                "Edmonton Oilers": "6",
                "Florida Panthers": "26",
                "Los Angeles Kings": "8",
                "Minnesota Wild": "30",
                "Montreal Canadiens": "10",
                "Nashville Predators": "27",
                "New Jersey Devils": "11",
                "New York Islanders": "12",
                "New York Rangers": "13",
                "Ottawa Senators": "14",
                "Philadelphia Flyers": "15",
                "Pittsburgh Penguins": "16",
                "San Jose Sharks": "18",
                "Seattle Kraken": "124292",
                "St. Louis Blues": "19",
                "Tampa Bay Lightning": "20",
                "Toronto Maple Leafs": "21",
                "Utah Mammoth": "129764",
                "Vancouver Canucks": "22",
                "Vegas Golden Knights": "37",
                "Washington Capitals": "23",
                "Winnipeg Jets": "28",
            },
        }
        return team_mapping.get(sport, {}).get(team_name)


class EnsembleModel(BaseAnalysisModel):
    """Ensemble model: Weighted combination of all models using dynamic weighting"""

    def __init__(self):
        super().__init__()
        from ml.dynamic_weighting import DynamicModelWeighting
        from ml.player_stats_model import PlayerStatsModel

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
        """Combine predictions from all models using dynamic weights"""
        try:
            sport = game_info.get("sport")

            # Get predictions from all models
            predictions = {}
            for model_name, model in self.models.items():
                result = model.analyze_game_odds(game_id, odds_items, game_info)
                if result:
                    predictions[model_name] = result

            if not predictions:
                return None

            # Get dynamic weights for each model
            weights = self.weighting.get_model_weights(
                sport, "game", list(predictions.keys())
            )

            # Calculate weighted average confidence
            weighted_confidence = sum(
                predictions[model].confidence * weights[model]
                for model in predictions.keys()
            )

            # Use the prediction from the highest weighted model
            best_model = max(weights.items(), key=lambda x: x[1])[0]
            best_prediction = predictions[best_model]

            # Combine reasoning from top 3 models
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
        """Combine prop predictions from all models using dynamic weights"""
        try:
            sport = prop_item.get("sport")

            # Get predictions from all models
            predictions = {}
            for model_name, model in self.models.items():
                result = model.analyze_prop_odds(prop_item)
                if result:
                    predictions[model_name] = result

            if not predictions:
                return None

            # Get dynamic weights for each model
            weights = self.weighting.get_model_weights(
                sport, "prop", list(predictions.keys())
            )

            # Calculate weighted average confidence
            weighted_confidence = sum(
                predictions[model].confidence * weights[model]
                for model in predictions.keys()
            )

            # Use the prediction from the highest weighted model
            best_model = max(weights.items(), key=lambda x: x[1])[0]
            best_prediction = predictions[best_model]
            
            # Show top 3 models with weights
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


class NewsModel(BaseAnalysisModel):
    """Model based purely on news sentiment analysis"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        try:
            from news_features import get_team_sentiment

            sport = game_info.get("sport")
            home_team = game_info.get("home_team")
            away_team = game_info.get("away_team")

            if not all([sport, home_team, away_team]):
                return None

            home_sentiment = get_team_sentiment(sport, home_team)
            away_sentiment = get_team_sentiment(sport, away_team)

            if home_sentiment["news_count"] == 0 and away_sentiment["news_count"] == 0:
                return None

            sentiment_diff = (
                home_sentiment["sentiment_score"] - away_sentiment["sentiment_score"]
            )
            avg_impact = (
                home_sentiment["impact_score"] + away_sentiment["impact_score"]
            ) / 2

            if abs(sentiment_diff) < 0.05:
                return None

            prediction = home_team if sentiment_diff > 0 else away_team
            confidence = min(0.75, 0.5 + (abs(sentiment_diff) * avg_impact * 0.5))

            return AnalysisResult(
                game_id=game_id,
                bookmaker=odds_items[0].get("bookmaker") if odds_items else "unknown",
                model="news",
                analysis_type="game",
                sport=sport,
                home_team=home_team,
                away_team=away_team,
                commence_time=game_info.get("commence_time"),
                player_name=None,
                prediction=prediction,
                confidence=confidence,
                reasoning=f"Recent news favors {prediction}: {home_sentiment['news_count']} home stories, {away_sentiment['news_count']} away stories. Positive buzz around {prediction}",
            )
        except Exception as e:
            logger.error(f"Error in news model: {e}")
            return None

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        return None


class FundamentalsModel(BaseAnalysisModel):
    """Fundamentals-based model using opponent-adjusted metrics, Elo, weather, and fatigue"""
    
    def __init__(self, dynamodb_table=None):
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
            
            # Soccer and MLB not supported - ESPN doesn't provide team stats
            return 0.0
            
        except Exception as e:
            logger.error(f"Error comparing metrics: {e}")
            return 0.0


class ModelFactory:
    """Factory for creating analysis models"""

    _models = {
        "consensus": ConsensusModel,
        "value": ValueModel,
        "momentum": MomentumModel,
        "contrarian": ContrarianModel,
        "hot_cold": HotColdModel,
        "rest_schedule": RestScheduleModel,
        "matchup": MatchupModel,
        "injury_aware": InjuryAwareModel,
        "ensemble": EnsembleModel,
        "news": NewsModel,
        "fundamentals": FundamentalsModel,
    }

    @classmethod
    def create_model(cls, model_name: str) -> BaseAnalysisModel:
        """Create and return a model instance"""
        # Special case for player_stats - lazy import to avoid circular dependency
        if model_name == "player_stats":
            from ml.player_stats_model import PlayerStatsModel
            return PlayerStatsModel()
        
        if model_name not in cls._models:
            raise ValueError(
                f"Unknown model: {model_name}. Available: {list(cls._models.keys()) + ['player_stats']}"
            )

        return cls._models[model_name]()

    @classmethod
    def get_available_models(cls) -> List[str]:
        """Get list of available model names"""
        return list(cls._models.keys()) + ["player_stats"]

    def _calculate_std(self, values: List[float]) -> float:
        """Calculate standard deviation"""
        if len(values) <= 1:
            return 0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return math.sqrt(variance)
