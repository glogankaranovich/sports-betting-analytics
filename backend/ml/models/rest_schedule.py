"""RestSchedule Model - Analyze rest days and travel fatigue"""

import logging
from typing import Dict, List, Optional

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class RestScheduleModel(BaseModel):
    """Model that analyzes rest days, back-to-back games, and travel fatigue"""

    def __init__(self, dynamodb_table=None):
        import os
        import boto3

        self.table = dynamodb_table
        if not self.table:
            dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
            table_name = os.getenv("DYNAMODB_TABLE", "carpool-bets-v2-dev")
            self.table = dynamodb.Table(table_name)
        
        from travel_fatigue_calculator import TravelFatigueCalculator
        self.fatigue_calculator = TravelFatigueCalculator()

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        sport = game_info.get("sport")
        home_team = game_info.get("home_team")
        away_team = game_info.get("away_team")
        game_date = game_info.get("commence_time")

        try:
            home_fatigue = self.fatigue_calculator.calculate_fatigue_score(home_team, sport, game_date)
            away_fatigue = self.fatigue_calculator.calculate_fatigue_score(away_team, sport, game_date)
            
            home_advantage = (100 - home_fatigue['fatigue_score']) - (100 - away_fatigue['fatigue_score'])
            home_advantage = home_advantage / 20
            
            confidence = 0.5 + (abs(home_advantage) * 0.05)
            confidence = max(0.3, min(0.85, confidence))
            
            pick = home_team if home_advantage > 0 else away_team
            
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
        sport = prop_item.get("sport")
        player_name = prop_item.get("player_name", "")
        game_date = prop_item.get("commence_time")
        line = prop_item.get("point", 0)

        team = self._get_player_team(sport, player_name.lower().replace(" ", "_"))
        if not team:
            return None

        rest_score = self._get_rest_score(sport, team, game_date, is_home=True)

        confidence = 0.5 + (rest_score * 0.03)
        confidence = max(0.3, min(0.8, confidence))

        if rest_score > 1:
            prediction = f"Over {line}"
            reasoning = f"Team well-rested (score: {rest_score:.1f}). Player likely to perform above line."
        else:
            prediction = f"Under {line}"
            reasoning = f"Team fatigued (score: {rest_score:.1f}). Player likely to underperform."

        return AnalysisResult(
            game_id=prop_item.get("event_id", "unknown"),
            model="rest_schedule",
            analysis_type="prop",
            sport=sport,
            home_team=prop_item.get("home_team"),
            away_team=prop_item.get("away_team"),
            player_name=player_name,
            market_key=prop_item.get("market_key"),
            commence_time=game_date,
            prediction=prediction,
            confidence=confidence,
            reasoning=reasoning,
            recommended_odds=-110,
        )

    def _get_rest_score(
        self, sport: str, team: str, game_date: str, is_home: bool
    ) -> float:
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

            current_game = items[0]
            rest_days = current_game.get("rest_days", 2)

            score = 0.0

            if rest_days >= 3:
                score += 3.0
            elif rest_days == 2:
                score += 1.5
            elif rest_days == 1:
                score += 0.5
            elif rest_days == 0:
                score -= 3.0

            if is_home:
                score += 1.0
            else:
                score -= 0.5

            return score

        except Exception as e:
            logger.error(f"Error getting rest score: {e}", exc_info=True)
            return 0.0

    def _get_player_team(self, sport: str, player_name: str) -> Optional[str]:
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
