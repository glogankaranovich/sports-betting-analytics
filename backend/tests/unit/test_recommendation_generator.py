import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recommendation_generator import RecommendationGenerator  # noqa: E402


class TestRecommendationGenerator(unittest.TestCase):
    def setUp(self):
        self.table_name = "test-table"

    @patch("recommendation_generator.boto3")
    @patch("recommendation_generator.RecommendationStorage")
    @patch("recommendation_generator.BetRecommendationEngine")
    def test_init(self, mock_engine, mock_storage, mock_boto3):
        """Test RecommendationGenerator initialization"""
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table

        RecommendationGenerator(self.table_name)

        mock_boto3.resource.assert_called_once_with("dynamodb", region_name="us-east-1")
        mock_dynamodb.Table.assert_called_once_with(self.table_name)
        mock_engine.assert_called_once()
        mock_storage.assert_called_once_with(self.table_name)

    @patch("recommendation_generator.boto3")
    def test_get_active_sports(self, mock_boto3):
        """Test getting active sports from predictions"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        # Mock scan response
        mock_table.scan.return_value = {
            "Items": [
                {"sport": "NBA"},
                {"sport": "NFL"},
                {"sport": "NBA"},  # Duplicate should be deduplicated
            ]
        }

        generator = RecommendationGenerator(self.table_name)
        sports = generator._get_active_sports()

        # Verify scan was called
        mock_table.scan.assert_called_once()

        # Verify results
        self.assertEqual(len(sports), 2)
        self.assertIn("NBA", sports)
        self.assertIn("NFL", sports)

    @patch("recommendation_generator.boto3")
    def test_get_active_sports_fallback(self, mock_boto3):
        """Test fallback when no sports found"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        # Mock empty response
        mock_table.scan.return_value = {"Items": []}

        generator = RecommendationGenerator(self.table_name)
        sports = generator._get_active_sports()

        # Should return default fallback
        self.assertEqual(sports, ["NBA", "NFL"])

    @patch("recommendation_generator.boto3")
    def test_get_recent_predictions(self, mock_boto3):
        """Test getting recent predictions"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        # Mock scan response
        mock_table.scan.return_value = {
            "Items": [
                {
                    "pk": "PRED#GAME#game123",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "home_win_probability": 0.6,
                    "away_win_probability": 0.4,
                    "confidence_score": 0.8,
                    "home_odds": -120,
                    "away_odds": 100,
                    "bookmaker": "DraftKings",
                }
            ]
        }

        generator = RecommendationGenerator(self.table_name)
        predictions = generator._get_recent_predictions("NBA", "consensus")

        # Verify scan was called
        mock_table.scan.assert_called_once()

        # Verify results
        self.assertEqual(len(predictions), 1)
        pred = predictions[0]
        self.assertEqual(pred["game_id"], "game123")
        self.assertEqual(pred["prediction"]["home_team"], "Lakers")
        self.assertEqual(pred["odds"]["home_odds"], -120.0)


if __name__ == "__main__":
    unittest.main()
