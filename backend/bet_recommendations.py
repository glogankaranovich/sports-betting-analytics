"""
Bet Recommendation Engine - Converts predictions into actionable betting recommendations
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class RiskLevel(Enum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


@dataclass
class BetRecommendation:
    game_id: str
    sport: str
    bet_type: str  # "home", "away", "over", "under"
    team_or_player: str
    market: str  # "moneyline", "spread", "total", "player_points", etc.

    # Prediction data
    predicted_probability: float
    confidence_score: float
    expected_value: float  # Edge over bookmaker

    # Recommendation data
    risk_level: RiskLevel
    recommended_bet_amount: float
    potential_payout: float
    bookmaker: str
    odds: float

    # Reasoning
    reasoning: str


class BetRecommendationEngine:
    def __init__(self, default_bankroll: float = 1000.0):
        self.default_bankroll = default_bankroll

        # Risk level multipliers for Kelly Criterion
        self.risk_multipliers = {
            RiskLevel.CONSERVATIVE: 0.25,  # 25% of Kelly
            RiskLevel.MODERATE: 0.5,  # 50% of Kelly
            RiskLevel.AGGRESSIVE: 1.0,  # Full Kelly
        }

        # Minimum edge required for each risk level
        self.min_edge_thresholds = {
            RiskLevel.CONSERVATIVE: 0.15,  # 15% edge required
            RiskLevel.MODERATE: 0.10,  # 10% edge required
            RiskLevel.AGGRESSIVE: 0.05,  # 5% edge required
        }

    def generate_game_recommendations(
        self, game_prediction, game_odds_data
    ) -> List[BetRecommendation]:
        """Convert game prediction into bet recommendations for all risk levels"""
        recommendations = []

        # Extract game info
        game_id = game_prediction.game_id
        sport = game_prediction.sport
        home_team = game_odds_data.get("home_team", "Home")
        away_team = game_odds_data.get("away_team", "Away")

        # Check home team bet
        home_recs = self._evaluate_bet(
            game_id=game_id,
            sport=sport,
            bet_type="home",
            team_or_player=home_team,
            market="moneyline",
            predicted_prob=game_prediction.home_win_probability,
            confidence=game_prediction.confidence_score,
            odds_data=game_odds_data.get("odds", {}),
            side="home",
        )
        recommendations.extend(home_recs)

        # Check away team bet
        away_recs = self._evaluate_bet(
            game_id=game_id,
            sport=sport,
            bet_type="away",
            team_or_player=away_team,
            market="moneyline",
            predicted_prob=game_prediction.away_win_probability,
            confidence=game_prediction.confidence_score,
            odds_data=game_odds_data.get("odds", {}),
            side="away",
        )
        recommendations.extend(away_recs)

        return recommendations

    def _evaluate_bet(
        self,
        game_id: str,
        sport: str,
        bet_type: str,
        team_or_player: str,
        market: str,
        predicted_prob: float,
        confidence: float,
        odds_data: Dict,
        side: str,
    ) -> List[BetRecommendation]:
        """Evaluate a single bet across all risk levels and bookmakers"""
        recommendations = []

        # Find best odds for this side across all bookmakers
        best_odds = None
        best_bookmaker = None

        for bookmaker, bookmaker_data in odds_data.items():
            h2h_market = bookmaker_data.get("h2h", {})
            outcomes = h2h_market.get("outcomes", [])

            for outcome in outcomes:
                if self._matches_side(outcome["name"], side, team_or_player):
                    odds = outcome["price"]
                    if best_odds is None or odds > best_odds:
                        best_odds = odds
                        best_bookmaker = bookmaker

        if not best_odds or not best_bookmaker:
            return recommendations

        # Convert American odds to decimal
        decimal_odds = self._american_to_decimal(best_odds)
        implied_prob = 1 / decimal_odds

        # Calculate expected value
        expected_value = (predicted_prob * decimal_odds) - 1
        edge = expected_value / implied_prob if implied_prob > 0 else 0

        # Generate recommendations for each risk level
        for risk_level in RiskLevel:
            if edge >= self.min_edge_thresholds[risk_level]:
                # Calculate Kelly bet size
                kelly_fraction = (predicted_prob * decimal_odds - 1) / (
                    decimal_odds - 1
                )
                kelly_fraction = max(
                    0, min(0.25, kelly_fraction)
                )  # Cap at 25% of bankroll

                # Apply risk multiplier
                bet_fraction = kelly_fraction * self.risk_multipliers[risk_level]
                bet_amount = self.default_bankroll * bet_fraction
                bet_amount = max(
                    5, min(bet_amount, 100)
                )  # Min $5, Max $100 for defaults

                potential_payout = bet_amount * decimal_odds

                reasoning = (
                    f"{confidence:.1%} confidence, {edge:.1%} edge over bookmaker. "
                    f"Model predicts {predicted_prob:.1%} chance vs {implied_prob:.1%} implied."
                )

                recommendation = BetRecommendation(
                    game_id=game_id,
                    sport=sport,
                    bet_type=bet_type,
                    team_or_player=team_or_player,
                    market=market,
                    predicted_probability=predicted_prob,
                    confidence_score=confidence,
                    expected_value=expected_value,
                    risk_level=risk_level,
                    recommended_bet_amount=round(bet_amount, 2),
                    potential_payout=round(potential_payout, 2),
                    bookmaker=best_bookmaker,
                    odds=best_odds,
                    reasoning=reasoning,
                )

                recommendations.append(recommendation)

        return recommendations

    def _matches_side(self, outcome_name: str, side: str, team_or_player: str) -> bool:
        """Check if outcome matches the side we're evaluating"""
        if side in ["home", "away"]:
            return team_or_player.lower() in outcome_name.lower()
        elif side == "over":
            return "over" in outcome_name.lower()
        elif side == "under":
            return "under" in outcome_name.lower()
        return False

    def _american_to_decimal(self, american_odds: int) -> float:
        """Convert American odds to decimal odds"""
        if american_odds > 0:
            return (american_odds / 100) + 1
        else:
            return (100 / abs(american_odds)) + 1

    def get_top_recommendation(
        self,
        all_recommendations: List[BetRecommendation],
        risk_level: RiskLevel = RiskLevel.MODERATE,
    ) -> Optional[BetRecommendation]:
        """Get the top recommendation for a specific risk level"""
        filtered_recs = [r for r in all_recommendations if r.risk_level == risk_level]

        if not filtered_recs:
            return None

        # Sort by expected value * confidence (risk-adjusted expected value)
        return max(filtered_recs, key=lambda r: r.expected_value * r.confidence_score)
