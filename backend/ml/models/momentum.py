"""Momentum Model - Recent odds movement with fatigue adjustments"""

import logging
from typing import Dict, List

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class MomentumModel(BaseModel):
    """Momentum model: Based on recent odds movement with fatigue adjustments"""
    
    def __init__(self):
        super().__init__()
        from elo_calculator import EloCalculator
        from travel_fatigue_calculator import TravelFatigueCalculator
        
        self.fatigue_calculator = TravelFatigueCalculator()
        self.elo_calculator = EloCalculator()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        spread_items = [
            item
            for item in odds_items
            if "spreads" in item.get("sk", "") and "outcomes" in item
        ]

        if len(spread_items) < 2:
            return None

        spread_items.sort(key=lambda x: x.get("updated_at", ""))

        oldest = spread_items[0]
        newest = spread_items[-1]

        if len(oldest.get("outcomes", [])) < 2 or len(newest.get("outcomes", [])) < 2:
            return None

        old_spread = float(oldest["outcomes"][0].get("point", 0))
        new_spread = float(newest["outcomes"][0].get("point", 0))
        movement = new_spread - old_spread
        
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        game_date = game_info.get("commence_time")
        
        if movement < 0:
            prediction = home_team
        else:
            prediction = away_team
        
        fatigue_context = ""
        fatigue_adjustment = 0
        try:
            home_fatigue = self.fatigue_calculator.calculate_fatigue_score(home_team, sport, game_date)
            away_fatigue = self.fatigue_calculator.calculate_fatigue_score(away_team, sport, game_date)
            
            fatigue_diff = away_fatigue['fatigue_score'] - home_fatigue['fatigue_score']
            
            if abs(fatigue_diff) > 30:
                if fatigue_diff > 0:
                    fatigue_context = f" {away_team} fatigued (score: {away_fatigue['fatigue_score']}, {away_fatigue['days_rest']}d rest)."
                    if prediction == home_team:
                        fatigue_adjustment = 0.05
                else:
                    fatigue_context = f" {home_team} fatigued (score: {home_fatigue['fatigue_score']}, {home_fatigue['days_rest']}d rest)."
                    if prediction == away_team:
                        fatigue_adjustment = 0.05
        except Exception as e:
            logger.error(f"Error calculating fatigue: {e}")

        if abs(movement) > 1.0:
            confidence = 0.8
            reasoning = f"Big line shift: Spread moved from {abs(old_spread):.1f} to {abs(new_spread):.1f} points ({abs(movement):.1f} point change). Professional bettors are likely driving this move.{fatigue_context}"
        elif abs(movement) > 0.5:
            confidence = 0.7
            reasoning = f"Line is moving: Spread changed from {abs(old_spread):.1f} to {abs(new_spread):.1f} points. Sportsbooks adjusting based on betting patterns.{fatigue_context}"
        else:
            confidence = 0.6
            reasoning = f"Small line adjustment: Spread moved slightly from {abs(old_spread):.1f} to {abs(new_spread):.1f} points. Minor market change.{fatigue_context}"

        try:
            home_elo = self.elo_calculator.get_team_rating(sport, home_team)
            away_elo = self.elo_calculator.get_team_rating(sport, away_team)
            elo_diff = home_elo - away_elo
            
            if (movement < 0 and elo_diff > 50) or (movement > 0 and elo_diff < -50):
                confidence = min(confidence + 0.05, 0.95)
        except Exception as e:
            logger.error(f"Error getting Elo ratings: {e}")

        confidence = self._adjust_confidence(confidence + fatigue_adjustment, "momentum", sport)

        return AnalysisResult(
            game_id=game_id,
            model="momentum",
            analysis_type="game",
            sport=sport,
            home_team=home_team,
            away_team=away_team,
            commence_time=game_date,
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
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

            over_decimal = self.american_to_decimal(over_price)
            under_decimal = self.american_to_decimal(under_price)

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            if over_price <= -120:
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = 0.75
                reasoning = f"Sharp action on Over: {over_price} indicates heavy betting"
            elif under_price <= -120:
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = 0.75
                reasoning = f"Sharp action on Under: {under_price} indicates heavy betting"
            elif over_prob > under_prob * 1.1:
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = 0.7
                reasoning = f"Momentum favors Over: {over_price} vs {under_price}"
            elif under_prob > over_prob * 1.1:
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = 0.7
                reasoning = f"Momentum favors Under: {under_price} vs {over_price}"
            else:
                return None

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
