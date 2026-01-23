import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from model_analytics import ModelAnalytics  # noqa: E402


class TestModelAnalytics(unittest.TestCase):
    def setUp(self):
        self.table_name = "test-table"
        self.mock_table = Mock()

    @patch("model_analytics.boto3")
    def test_init(self, mock_boto3):
        mock_dynamodb = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = self.mock_table

        ModelAnalytics(self.table_name)

        mock_boto3.resource.assert_called_once_with("dynamodb", region_name="us-east-1")
        mock_dynamodb.Table.assert_called_once_with(self.table_name)

    @patch("model_analytics.boto3")
    def test_get_model_performance_summary(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        self.mock_table.scan.return_value = {
            "Items": [
                {
                    "model": "odds_movement",
                    "sport": "basketball_nba",
                    "analysis_correct": True,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
                {
                    "model": "odds_movement",
                    "sport": "basketball_nba",
                    "analysis_correct": False,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
                {
                    "model": "team_stats",
                    "sport": "americanfootball_nfl",
                    "analysis_correct": True,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
            ]
        }

        analytics = ModelAnalytics(self.table_name)
        summary = analytics.get_model_performance_summary()

        self.assertIn("odds_movement", summary)
        self.assertEqual(summary["odds_movement"]["total_analyses"], 2)
        self.assertEqual(summary["odds_movement"]["correct_analyses"], 1)
        self.assertEqual(summary["odds_movement"]["accuracy"], 50.0)

        self.assertIn("team_stats", summary)
        self.assertEqual(summary["team_stats"]["total_analyses"], 1)
        self.assertEqual(summary["team_stats"]["correct_analyses"], 1)
        self.assertEqual(summary["team_stats"]["accuracy"], 100.0)

    @patch("model_analytics.boto3")
    def test_get_model_performance_by_sport(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        self.mock_table.scan.return_value = {
            "Items": [
                {
                    "model": "odds_movement",
                    "sport": "basketball_nba",
                    "analysis_correct": True,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
                {
                    "model": "team_stats",
                    "sport": "basketball_nba",
                    "analysis_correct": True,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
            ]
        }

        analytics = ModelAnalytics(self.table_name)
        summary = analytics.get_model_performance_by_sport()

        self.assertIn("odds_movement", summary)
        self.assertIn("basketball_nba", summary["odds_movement"])
        self.assertEqual(summary["odds_movement"]["basketball_nba"]["total"], 1)
        self.assertEqual(summary["odds_movement"]["basketball_nba"]["correct"], 1)
        self.assertEqual(summary["odds_movement"]["basketball_nba"]["accuracy"], 100.0)


if __name__ == "__main__":
    unittest.main()
