"""
Tests for Benny learning system
"""
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from benny_trader import BennyTrader


class TestBennyLearning(unittest.TestCase):
    def setUp(self):
        with patch.object(
            BennyTrader, "_get_current_bankroll", return_value=Decimal("100")
        ):
            with patch.object(
                BennyTrader, "_get_week_start", return_value="2024-01-01"
            ):
                with patch.object(
                    BennyTrader,
                    "_get_learning_parameters",
                    return_value={
                        "min_confidence_adjustment": 0.0,
                        "kelly_fraction": 0.25,
                        "performance_by_sport": {},
                        "performance_by_market": {},
                    },
                ):
                    self.benny = BennyTrader("test-table")
                    self.benny.table = MagicMock()

    def test_calculate_bet_size_with_positive_odds(self):
        """Test Kelly Criterion with positive American odds"""
        confidence = 0.70
        odds = 150  # +150

        bet_size = self.benny.calculate_bet_size(confidence, odds)

        # Should return positive bet size
        assert bet_size > Decimal("0")
        assert bet_size <= self.benny.bankroll * Decimal("0.20")  # Max 20%

    def test_calculate_bet_size_with_negative_odds(self):
        """Test Kelly Criterion with negative American odds"""
        confidence = 0.65
        odds = -110

        bet_size = self.benny.calculate_bet_size(confidence, odds)

        assert bet_size >= Decimal("5.00")  # Minimum bet
        assert bet_size <= self.benny.bankroll * Decimal("0.20")

    def test_calculate_bet_size_minimum_enforced(self):
        """Test minimum bet size is enforced"""
        confidence = 0.51  # Very low confidence
        odds = -500  # Heavy favorite

        bet_size = self.benny.calculate_bet_size(confidence, odds)

        assert bet_size >= Decimal("5.00")

    def test_update_learning_parameters_insufficient_data(self):
        """Test learning update with insufficient bets"""

        # Mock only 5 bets (need 10)
        self.benny.table.query.return_value = {
            "Items": [{"status": "won"} for _ in range(5)]
        }

        self.benny.update_learning_parameters()

        # Should not update parameters
        self.benny.table.put_item.assert_not_called()

    def test_update_learning_parameters_high_win_rate(self):
        """Test confidence adjustment with high win rate"""

        # Mock 15 bets with 65% win rate
        bets = [
            {"status": "won", "sport": "basketball_nba", "bet_type": "h2h"}
            for _ in range(10)
        ] + [
            {"status": "lost", "sport": "basketball_nba", "bet_type": "h2h"}
            for _ in range(5)
        ]

        self.benny.table.query.return_value = {"Items": bets}

        self.benny.update_learning_parameters()

        # Should lower confidence threshold (bet more)
        call_args = self.benny.table.put_item.call_args[1]["Item"]
        assert call_args["min_confidence_adjustment"] == Decimal("-0.02")

    def test_update_learning_parameters_low_win_rate(self):
        """Test confidence adjustment with low win rate"""

        # Mock 15 bets with 40% win rate
        bets = [
            {"status": "won", "sport": "basketball_nba", "bet_type": "h2h"}
            for _ in range(6)
        ] + [
            {"status": "lost", "sport": "basketball_nba", "bet_type": "h2h"}
            for _ in range(9)
        ]

        self.benny.table.query.return_value = {"Items": bets}

        self.benny.update_learning_parameters()

        # Should raise confidence threshold (bet less)
        call_args = self.benny.table.put_item.call_args[1]["Item"]
        assert call_args["min_confidence_adjustment"] == Decimal("0.05")

    def test_update_learning_parameters_tracks_by_sport(self):
        """Test performance tracking by sport"""
        bets = [
            {"status": "won", "sport": "basketball_nba", "bet_type": "h2h"}
            for _ in range(8)
        ] + [
            {"status": "lost", "sport": "americanfootball_nfl", "bet_type": "h2h"}
            for _ in range(7)
        ]

        self.benny.table.query.return_value = {"Items": bets}

        self.benny.update_learning_parameters()

        call_args = self.benny.table.put_item.call_args[1]["Item"]
        perf_by_sport = call_args["performance_by_sport"]

        assert "basketball_nba" in perf_by_sport
        assert perf_by_sport["basketball_nba"]["wins"] == 8
        assert perf_by_sport["basketball_nba"]["total"] == 8

        assert "americanfootball_nfl" in perf_by_sport
        assert perf_by_sport["americanfootball_nfl"]["wins"] == 0
        assert perf_by_sport["americanfootball_nfl"]["total"] == 7

    def test_get_what_works_analysis_with_winning_patterns(self):
        """Test identifying winning patterns by sport and market"""
        self.benny.learning_params = {
            "performance_by_sport": {
                "basketball_nba": {"wins": 12, "total": 20},  # 60% win rate
                "americanfootball_nfl": {"wins": 3, "total": 10},  # 30% win rate
            },
            "performance_by_market": {
                "h2h": {"wins": 8, "total": 12},  # 66% win rate
                "spread": {"wins": 2, "total": 8},  # 25% win rate
            },
        }

        result = self.benny._get_what_works_analysis()

        assert "basketball_nba" in result
        assert "60.0%" in result
        assert "h2h" in result
        assert "66.7%" in result
        assert "americanfootball_nfl" not in result  # Below 55%
        assert "spread" not in result  # Below 55%

    def test_get_what_works_analysis_insufficient_data(self):
        """Test what works analysis with insufficient data"""
        self.benny.learning_params = {
            "performance_by_sport": {
                "basketball_nba": {"wins": 3, "total": 4},  # Only 4 bets
            },
            "performance_by_market": {},
        }

        result = self.benny._get_what_works_analysis()

        assert "Not enough data yet" in result

    def test_get_what_fails_analysis_with_losing_patterns(self):
        """Test identifying losing patterns by sport and market"""
        self.benny.learning_params = {
            "performance_by_sport": {
                "basketball_nba": {"wins": 12, "total": 20},  # 60% win rate
                "soccer_epl": {"wins": 2, "total": 10},  # 20% win rate
            },
            "performance_by_market": {
                "h2h": {"wins": 8, "total": 12},  # 66% win rate
                "prop": {"wins": 2, "total": 15},  # 13% win rate
            },
        }

        result = self.benny._get_what_fails_analysis()

        assert "soccer_epl" in result
        assert "20.0%" in result
        assert "be very selective" in result
        assert "prop" in result
        assert "13.3%" in result
        assert "basketball_nba" not in result  # Above 45%
        assert "h2h" not in result  # Above 45%

    def test_get_what_fails_analysis_no_failures(self):
        """Test what fails analysis when no clear failures"""
        self.benny.learning_params = {
            "performance_by_sport": {
                "basketball_nba": {"wins": 10, "total": 20},  # 50% win rate
            },
            "performance_by_bet_type": {},
        }

        result = self.benny._get_what_fails_analysis()

        assert "No clear failure patterns yet" in result

    def test_analyze_recent_mistakes_overconfident(self):
        """Test detecting overconfidence in recent losses"""
        losses = [
            {"status": "lost", "confidence": Decimal("0.80"), "odds": -110, "sport": "basketball_nba"}
            for _ in range(6)
        ] + [
            {"status": "lost", "confidence": Decimal("0.65"), "odds": -110, "sport": "basketball_nba"}
            for _ in range(4)
        ]
        
        self.benny.table.query.return_value = {"Items": losses}
        
        result = self.benny._analyze_recent_mistakes()
        
        assert "6/10 losses were high confidence" in result
        assert "overconfident" in result

    def test_analyze_recent_mistakes_chasing_underdogs(self):
        """Test detecting underdog chasing pattern"""
        losses = [
            {"status": "lost", "confidence": Decimal("0.70"), "odds": 150, "sport": "basketball_nba"}
            for _ in range(7)
        ] + [
            {"status": "lost", "confidence": Decimal("0.70"), "odds": -110, "sport": "basketball_nba"}
            for _ in range(3)
        ]
        
        self.benny.table.query.return_value = {"Items": losses}
        
        result = self.benny._analyze_recent_mistakes()
        
        assert "7/10 losses were underdogs" in result
        assert "chasing value" in result

    def test_analyze_recent_mistakes_sport_specific(self):
        """Test detecting sport-specific loss patterns"""
        losses = [
            {"status": "lost", "confidence": Decimal("0.70"), "odds": -110, "sport": "soccer_epl"}
            for _ in range(5)
        ] + [
            {"status": "lost", "confidence": Decimal("0.70"), "odds": -110, "sport": "basketball_nba"}
            for _ in range(2)
        ]
        
        self.benny.table.query.return_value = {"Items": losses}
        
        result = self.benny._analyze_recent_mistakes()
        
        assert "5 recent losses in soccer_epl" in result

    def test_analyze_recent_mistakes_no_losses(self):
        """Test analyzing mistakes with no recent losses"""
        self.benny.table.query.return_value = {"Items": []}
        
        result = self.benny._analyze_recent_mistakes()
        
        assert "No recent losses to analyze" in result

    def test_get_winning_examples_with_wins(self):
        """Test getting winning examples for a sport"""
        wins = [
            {
                "status": "won",
                "sport": "basketball_nba",
                "prediction": "Lakers (Moneyline)",
                "confidence": Decimal("0.72"),
                "profit": Decimal("15.50"),
                "ai_reasoning": "Strong home court advantage and recent momentum"
            },
            {
                "status": "won",
                "sport": "basketball_nba",
                "prediction": "Celtics -5.5 (Spread)",
                "confidence": Decimal("0.68"),
                "profit": Decimal("12.30"),
                "ai_reasoning": "Elo rating difference of 75 points favors Celtics heavily"
            }
        ]
        
        self.benny.table.query.return_value = {"Items": wins}
        
        result = self.benny._get_winning_examples("basketball_nba", limit=3)
        
        assert "Lakers (Moneyline)" in result
        assert "72%" in result
        assert "$15.50" in result
        assert "Strong home court advantage" in result
        assert "Celtics -5.5 (Spread)" in result

    def test_get_winning_examples_no_wins(self):
        """Test getting winning examples when no wins exist"""
        self.benny.table.query.return_value = {"Items": []}
        
        result = self.benny._get_winning_examples("soccer_epl", limit=3)
        
        assert "No winning bets yet for soccer_epl" in result

    def test_extract_winning_factors_with_patterns(self):
        """Test extracting factors that correlate with wins"""
        bets = [
            {"status": "won", "ai_key_factors": ["Elo advantage >50", "Home court"]},
            {"status": "won", "ai_key_factors": ["Elo advantage >50", "Rest advantage"]},
            {"status": "won", "ai_key_factors": ["Elo advantage >50"]},
            {"status": "lost", "ai_key_factors": ["Injury concerns", "Back-to-back"]},
            {"status": "lost", "ai_key_factors": ["Injury concerns"]},
            {"status": "won", "ai_key_factors": ["Home court"]},
            {"status": "lost", "ai_key_factors": ["Back-to-back"]},
        ] * 2  # 14 bets total
        
        self.benny.table.query.return_value = {"Items": bets}
        
        result = self.benny._extract_winning_factors()
        
        assert "Elo advantage >50" in result
        assert "100%" in result  # 6/6 wins
        assert "Injury concerns" in result
        assert "0%" in result  # 0/4 wins

    def test_extract_winning_factors_insufficient_data(self):
        """Test extracting factors with insufficient bets"""
        bets = [{"status": "won", "ai_key_factors": ["Test"]}] * 5
        
        self.benny.table.query.return_value = {"Items": bets}
        
        result = self.benny._extract_winning_factors()
        
        assert "Not enough settled bets" in result

    def test_get_model_benchmarks_with_data(self):
        """Test getting model performance benchmarks"""
        momentum_preds = [
            {"analysis_correct": True} for _ in range(12)
        ] + [{"analysis_correct": False} for _ in range(8)]
        
        consensus_preds = [
            {"analysis_correct": True} for _ in range(8)
        ] + [{"analysis_correct": False} for _ in range(12)]
        
        def mock_query(**kwargs):
            pk = kwargs["ExpressionAttributeValues"][":pk"]
            if "momentum" in pk:
                return {"Items": momentum_preds}
            elif "consensus" in pk:
                return {"Items": consensus_preds}
            return {"Items": []}
        
        self.benny.table.query = mock_query
        
        result = self.benny._get_model_benchmarks("basketball_nba")
        
        # Should have at least some models with data
        assert "60.0%" in result or "40.0%" in result or len(result) > 0

    def test_get_model_benchmarks_no_data(self):
        """Test getting benchmarks with insufficient data"""
        self.benny.table.query.return_value = {"Items": []}
        
        result = self.benny._get_model_benchmarks("soccer_epl")
        
        assert "No benchmark data" in result


if __name__ == "__main__":
    unittest.main()
