"""
Test the bet recommendation engine
"""

from bet_recommendations import BetRecommendationEngine, RiskLevel
from ml.models import GamePrediction


def test_recommendation_engine():
    """Test basic recommendation generation"""
    engine = BetRecommendationEngine(default_bankroll=1000.0)

    # Mock game prediction
    game_prediction = GamePrediction(
        game_id="test_game_1",
        sport="americanfootball_nfl",
        home_win_probability=0.65,  # 65% chance
        away_win_probability=0.35,  # 35% chance
        confidence_score=0.78,  # 78% confidence
        value_bets=[],
    )

    # Mock odds data
    game_odds_data = {
        "game_id": "test_game_1",
        "home_team": "Kansas City Chiefs",
        "away_team": "Denver Broncos",
        "odds": {
            "betmgm": {
                "h2h": {
                    "outcomes": [
                        {"name": "Kansas City Chiefs", "price": -120},  # Implied ~55%
                        {"name": "Denver Broncos", "price": 100},  # Implied ~50%
                    ]
                }
            }
        },
    }

    # Generate recommendations
    recommendations = engine.generate_game_recommendations(
        game_prediction, game_odds_data
    )

    print(f"Generated {len(recommendations)} recommendations:")
    for rec in recommendations:
        print(f"\n{rec.risk_level.value.upper()} - {rec.team_or_player}")
        print(f"  Bet: ${rec.recommended_bet_amount}")
        print(f"  Payout: ${rec.potential_payout}")
        print(f"  Edge: {rec.expected_value:.1%}")
        print(f"  Reasoning: {rec.reasoning}")

    # Get top recommendation
    top_rec = engine.get_top_recommendation(recommendations, RiskLevel.MODERATE)
    if top_rec:
        print("\n🎯 TOP RECOMMENDATION (Moderate Risk):")
        print(f"Bet ${top_rec.recommended_bet_amount} on {top_rec.team_or_player}")
        print(f"Potential payout: ${top_rec.potential_payout}")
        print(f"Reasoning: {top_rec.reasoning}")


if __name__ == "__main__":
    test_recommendation_engine()
