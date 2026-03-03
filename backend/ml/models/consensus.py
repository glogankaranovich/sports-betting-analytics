"""Consensus Model - Average across all bookmakers with Elo adjustments"""

import logging
import os
from typing import Any, Dict, List

import boto3

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class ConsensusModel(BaseModel):
    """Consensus model: Average across all bookmakers with Elo adjustments"""
    
    def __init__(self):
        super().__init__()
        
        from elo_calculator import EloCalculator
        
        self.elo_calculator = EloCalculator()
        self.dynamodb = boto3.resource("dynamodb")
        table_name = os.getenv("DYNAMODB_TABLE")
        self.table = self.dynamodb.Table(table_name) if table_name else None

    def _get_line_movement(self, game_id: str, bookmaker: str = "fanduel") -> Dict[str, Any]:
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
        
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        
        try:
            home_elo = self.elo_calculator.get_team_rating(sport, home_team)
            away_elo = self.elo_calculator.get_team_rating(sport, away_team)
            elo_diff = home_elo - away_elo
            
            elo_context = ""
            if abs(elo_diff) > 100:
                if (avg_spread < 0 and elo_diff > 50) or (avg_spread > 0 and elo_diff < -50):
                    confidence = min(confidence + 0.05, 0.95)
                    elo_context = f" Elo ratings confirm: {home_team} {home_elo:.0f} vs {away_team} {away_elo:.0f}."
                elif (avg_spread < 0 and elo_diff < -50) or (avg_spread > 0 and elo_diff > 50):
                    confidence = max(confidence - 0.05, 0.55)
                    elo_context = f" Elo ratings suggest caution: {home_team} {home_elo:.0f} vs {away_team} {away_elo:.0f}."
        except Exception as e:
            logger.error(f"Error getting Elo ratings: {e}")
            elo_context = ""

        line_context = ""
        line_movement = self._get_line_movement(game_id)
        if line_movement:
            if line_movement["is_rlm"]:
                confidence = min(confidence + 0.05, 0.95)
                line_context = f" Sharp money detected (RLM)."
            elif abs(line_movement["movement"]) > 1.5:
                line_context = f" Line moved {abs(line_movement['movement']):.1f} points."

        confidence = self._adjust_confidence(confidence, "consensus", sport)

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
            prediction=home_team if avg_spread < 0 else away_team,
            confidence=confidence,
            reasoning=f"{len(spreads)} sportsbooks agree: {home_team} favored by {abs(avg_spread):.1f} points. Average payout odds: {avg_odds:+d}.{elo_context}{line_context}",
            recommended_odds=avg_odds,
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
            over_prob_fair = over_prob / total_prob
            under_prob_fair = under_prob / total_prob

            if over_prob_fair > under_prob_fair:
                prediction = f"Over {prop_item.get('point', 'N/A')}"
                confidence = over_prob_fair
            else:
                prediction = f"Under {prop_item.get('point', 'N/A')}"
                confidence = under_prob_fair

            return AnalysisResult(
                game_id=prop_item.get("event_id", "unknown"),
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
