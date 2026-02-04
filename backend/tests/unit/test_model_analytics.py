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

        # Track which PKs return data
        test_data = {
            "VERIFIED#momentum#basketball_nba#game": [
                {
                    "model": "momentum",
                    "sport": "basketball_nba",
                    "analysis_type": "game",
                    "analysis_correct": True,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
                {
                    "model": "momentum",
                    "sport": "basketball_nba",
                    "analysis_type": "game",
                    "analysis_correct": False,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
            ]
        }

        def mock_query(**kwargs):
            pk = kwargs.get("ExpressionAttributeValues", {}).get(":pk", "")
            return {"Items": test_data.get(pk, [])}

        self.mock_table.query.side_effect = mock_query

        analytics = ModelAnalytics(self.table_name)
        summary = analytics.get_model_performance_summary()

        self.assertIn("momentum", summary)
        self.assertEqual(summary["momentum"]["total_analyses"], 2)
        self.assertEqual(summary["momentum"]["correct_analyses"], 1)
        self.assertEqual(summary["momentum"]["accuracy"], 50.0)

    @patch("model_analytics.boto3")
    def test_get_model_performance_by_sport(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        # Track which PKs return data
        test_data = {
            "VERIFIED#momentum#basketball_nba#game": [
                {
                    "model": "momentum",
                    "sport": "basketball_nba",
                    "analysis_type": "game",
                    "analysis_correct": True,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
            ],
            "VERIFIED#value#basketball_nba#game": [
                {
                    "model": "value",
                    "sport": "basketball_nba",
                    "analysis_type": "game",
                    "analysis_correct": True,
                    "outcome_verified_at": "2025-01-01T00:00:00Z",
                },
            ],
        }

        def mock_query(**kwargs):
            pk = kwargs.get("ExpressionAttributeValues", {}).get(":pk", "")
            return {"Items": test_data.get(pk, [])}

        self.mock_table.query.side_effect = mock_query

        analytics = ModelAnalytics(self.table_name)
        summary = analytics.get_model_performance_by_sport()

        self.assertIn("momentum", summary)
        self.assertIn("basketball_nba", summary["momentum"])
        self.assertEqual(summary["momentum"]["basketball_nba"]["total"], 1)
        self.assertEqual(summary["momentum"]["basketball_nba"]["correct"], 1)
        self.assertEqual(summary["momentum"]["basketball_nba"]["accuracy"], 100.0)


if __name__ == "__main__":
    unittest.main()
