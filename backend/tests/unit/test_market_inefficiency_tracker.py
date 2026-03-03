"""Tests for market_inefficiency_tracker"""
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal

from market_inefficiency_tracker import MarketInefficiencyTracker


class TestMarketInefficiencyTracker(unittest.TestCase):
    """Test MarketInefficiencyTracker"""

    @patch("market_inefficiency_tracker.boto3")
    def test_init(self, mock_boto3):
        """Test initialization"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        tracker = MarketInefficiencyTracker("test-table")
        
        self.assertIsNotNone(tracker.table)
        mock_boto3.resource.return_value.Table.assert_called_once_with("test-table")

    @patch("market_inefficiency_tracker.boto3")
    def test_log_disagreement_significant(self, mock_boto3):
        """Test logging significant disagreement"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        tracker = MarketInefficiencyTracker("test-table")
        tracker.log_disagreement(
            game_id="game123",
            model="consensus",
            sport="basketball_nba",
            model_prediction="Lakers",
            model_spread=-5.5,
            market_spread=-3.0,
            confidence=0.75
        )
        
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]["Item"]
        self.assertEqual(call_args["game_id"], "game123")
        self.assertEqual(call_args["model"], "consensus")
        self.assertEqual(call_args["disagreement"], 2.5)

    @patch("market_inefficiency_tracker.boto3")
    def test_log_disagreement_insignificant(self, mock_boto3):
        """Test not logging insignificant disagreement"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        tracker = MarketInefficiencyTracker("test-table")
        tracker.log_disagreement(
            game_id="game123",
            model="consensus",
            sport="basketball_nba",
            model_prediction="Lakers",
            model_spread=-3.5,
            market_spread=-3.0,
            confidence=0.75
        )
        
        # Should not log disagreements < 1.0
        mock_table.put_item.assert_not_called()

    @patch("market_inefficiency_tracker.boto3")
    def test_get_profitable_disagreements_no_data(self, mock_boto3):
        """Test getting profitable disagreements with no data"""
        mock_table = Mock()
        mock_table.query.return_value = {"Items": []}
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        tracker = MarketInefficiencyTracker("test-table")
        result = tracker.get_profitable_disagreements("consensus", "basketball_nba", 30)
        
        self.assertEqual(result["total_disagreements"], 0)
        self.assertEqual(result["profitable_count"], 0)
        self.assertEqual(result["profitability_rate"], 0.0)

    @patch("market_inefficiency_tracker.boto3")
    def test_get_profitable_disagreements_with_outcomes(self, mock_boto3):
        """Test getting profitable disagreements with outcomes"""
        mock_table = Mock()
        mock_table.query.return_value = {
            "Items": [
                {"disagreement": 2.5, "was_correct": True},
                {"disagreement": 3.0, "was_correct": True},
                {"disagreement": 1.5, "was_correct": False},
            ]
        }
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        tracker = MarketInefficiencyTracker("test-table")
        result = tracker.get_profitable_disagreements("consensus", "basketball_nba", 30)
        
        self.assertEqual(result["total_disagreements"], 3)
        self.assertEqual(result["profitable_count"], 2)
        self.assertAlmostEqual(result["profitability_rate"], 2/3, places=2)
        self.assertAlmostEqual(result["avg_disagreement"], 2.33, places=2)


if __name__ == "__main__":
    unittest.main()
