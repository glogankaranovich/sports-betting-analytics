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
                        "performance_by_bet_type": {},
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


if __name__ == "__main__":
    unittest.main()
