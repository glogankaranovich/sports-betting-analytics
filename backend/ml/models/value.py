"""Value Model - Find best odds discrepancies"""

import logging
from typing import Dict, List

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class ValueModel(BaseModel):
    """Value model: Find best odds discrepancies"""

    def __init__(self):
        super().__init__()
        from elo_calculator import EloCalculator
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

        selected_spread = spreads[0]
        avg_spread = sum(s[0] for s in spreads) / len(spreads)
        spread_diff = selected_spread[0] - avg_spread
        
        if abs(spread_diff) < 0.5:
            return None
        
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        
        if spread_diff < 0:
            prediction = home_team
            reasoning = f"Value on {home_team}: {current_bookmaker} offers {abs(selected_spread[0]):.1f} spread vs market average {abs(avg_spread):.1f}. Getting {abs(spread_diff):.1f} extra points of value"
        else:
            prediction = away_team
            reasoning = f"Value on {away_team}: {current_bookmaker} offers +{abs(selected_spread[0]):.1f} spread vs market average +{abs(avg_spread):.1f}. Getting {abs(spread_diff):.1f} extra points of value"
        
        confidence = 0.7 if abs(spread_diff) > 1.0 else 0.6
        
        try:
            home_elo = self.elo_calculator.get_team_rating(sport, home_team)
            away_elo = self.elo_calculator.get_team_rating(sport, away_team)
            elo_diff = home_elo - away_elo
            
            if (prediction == home_team and elo_diff > 50) or \
               (prediction == away_team and elo_diff < -50):
                confidence = min(confidence + 0.05, 0.95)
        except Exception as e:
            logger.error(f"Error getting Elo ratings: {e}")
        
        confidence = self._adjust_confidence(confidence, "value", sport)

        return AnalysisResult(
            game_id=game_id,
            model="value",
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
        try:
            if "outcomes" not in prop_item or len(prop_item["outcomes"]) < 2:
                return None

            outcomes = prop_item["outcomes"]
            over_outcome = next((o for o in outcomes if o["name"] == "Over"), None)
            under_outcome = next((o for o in outcomes if o["name"] == "Under"), None)

            if not over_outcome or not under_outcome:
                return None

            over_decimal = self.american_to_decimal(int(over_outcome["price"]))
            under_decimal = self.american_to_decimal(int(under_outcome["price"]))

            over_prob = 1 / over_decimal
            under_prob = 1 / under_decimal

            total_prob = over_prob + under_prob
            vig = total_prob - 1.0

            over_prob_fair = over_prob / total_prob
            under_prob_fair = under_prob / total_prob

            if vig < 0.06:
                confidence = 0.75
                if over_prob_fair > under_prob_fair:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = f"Great odds: Sportsbook is offering better than usual pricing. Over is {over_prob_fair:.0%} likely based on the odds"
                else:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = f"Great odds: Sportsbook is offering better than usual pricing. Under is {under_prob_fair:.0%} likely based on the odds"
            elif vig < 0.08:
                confidence = 0.65
                if over_prob_fair > 0.52:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    reasoning = f"Good odds: Over has a slight edge at {over_prob_fair:.0%} probability. Better pricing than typical"
                elif under_prob_fair > 0.52:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    reasoning = f"Good odds: Under has a slight edge at {under_prob_fair:.0%} probability. Better pricing than typical"
                else:
                    return None
            else:
                if over_prob_fair > 0.55:
                    prediction = f"Over {prop_item.get('point', 'N/A')}"
                    confidence = 0.6
                    reasoning = f"Decent odds: Over is {over_prob_fair:.0%} likely. Worth considering despite higher sportsbook fees"
                elif under_prob_fair > 0.55:
                    prediction = f"Under {prop_item.get('point', 'N/A')}"
                    confidence = 0.6
                    reasoning = f"Decent odds: Under is {under_prob_fair:.0%} likely. Worth considering despite higher sportsbook fees"
                else:
                    return None

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
