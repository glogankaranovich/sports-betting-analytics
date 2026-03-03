"""Contrarian Model - Fade the public, follow sharp action"""

import logging
from typing import Dict, List

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class ContrarianModel(BaseModel):
    """Contrarian model: Fade the public, follow sharp action with Elo validation"""
    
    def __init__(self):
        from elo_calculator import EloCalculator
        self.elo_calculator = EloCalculator()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        spread_items = [item for item in odds_items 
                       if "spreads" in item.get("sk", "") and "outcomes" in item 
                       and len(item["outcomes"]) >= 2]

        if not spread_items:
            return None

        spread_items.sort(key=lambda x: x.get("updated_at", ""))

        if len(spread_items) < 2:
            return self._analyze_odds_imbalance(game_id, spread_items[0], game_info)

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
        
        elo_context = ""
        elo_boost = 0.0
        try:
            home_elo = self.elo_calculator.get_team_rating(sport, home_team)
            away_elo = self.elo_calculator.get_team_rating(sport, away_team)
            elo_diff = home_elo - away_elo
            
            if abs(elo_diff) > 50:
                if movement > 0 and elo_diff < 0:
                    elo_boost = 0.05
                    elo_context = f" Elo confirms: {away_team} ({away_elo:.0f}) > {home_team} ({home_elo:.0f})."
                elif movement < 0 and elo_diff > 0:
                    elo_boost = 0.05
                    elo_context = f" Elo confirms: {home_team} ({home_elo:.0f}) > {away_team} ({away_elo:.0f})."
                elif (movement > 0 and elo_diff > 50) or (movement < 0 and elo_diff < -50):
                    elo_boost = -0.1
                    elo_context = f" Caution: Elo suggests {home_team if elo_diff > 0 else away_team} is stronger."
        except Exception as e:
            logger.error(f"Error getting Elo ratings: {e}")

        if abs(movement) > 1.0:
            confidence = min(0.75 + elo_boost, 0.85)
            if movement > 0:
                prediction = away_team
                reasoning = f"Big money moving the line: Spread changed {abs(movement):.1f} points. Going against the crowd and following the big bettors.{elo_context}"
            else:
                prediction = home_team
                reasoning = f"Big money moving the line: Spread changed {abs(movement):.1f} points. Going against the crowd and following the big bettors.{elo_context}"
        elif abs(movement) > 0.5:
            confidence = min(0.65 + elo_boost, 0.75)
            if movement > 0:
                prediction = away_team
                reasoning = f"Line moving: Spread shifted {abs(movement):.1f} points. Smart money taking the opposite side of most bettors.{elo_context}"
            else:
                prediction = home_team
                reasoning = f"Line moving: Spread shifted {abs(movement):.1f} points. Smart money taking the opposite side of most bettors.{elo_context}"
        else:
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
        outcomes = spread_item.get("outcomes", [])
        if len(outcomes) < 2:
            return None

        home_outcome = outcomes[0]
        away_outcome = outcomes[1]

        home_price = float(home_outcome.get("price", -110))
        away_price = float(away_outcome.get("price", -110))
        home_spread = float(home_outcome.get("point", 0))

        price_diff = abs(home_price - away_price)

        if price_diff > 15:
            confidence = 0.70
            if home_price < away_price:
                prediction = game_info.get('home_team')
                reasoning = f"Uneven odds ({home_price}/{away_price}). Big money is on home team"
            else:
                prediction = game_info.get('away_team')
                reasoning = f"Uneven odds ({home_price}/{away_price}). Big money is on away team"
        elif price_diff > 10:
            confidence = 0.60
            if home_price < away_price:
                prediction = game_info.get('home_team')
                reasoning = f"Slightly uneven odds ({home_price}/{away_price}). Leaning home"
            else:
                prediction = game_info.get('away_team')
                reasoning = f"Slightly uneven odds ({home_price}/{away_price}). Leaning away"
        else:
            confidence = 0.55
            if home_spread < 0:
                prediction = game_info.get('away_team')
                reasoning = f"Betting against the favorite {game_info.get('home_team')}"
            else:
                prediction = game_info.get('home_team')
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

            price_diff = abs(over_price - under_price)

            if price_diff > 15:
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
                confidence = 0.55
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                reasoning = "Going against the crowd (most people bet overs)"

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
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
