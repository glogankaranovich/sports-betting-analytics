import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from recommendation_storage import RecommendationStorage  # noqa: E402
from bet_recommendations import BetRecommendation, RiskLevel  # noqa: E402


class TestRecommendationStorage(unittest.TestCase):
    def setUp(self):
        self.table_name = "test-table"

    @patch("recommendation_storage.boto3")
    def test_init(self, mock_boto3):
        """Test RecommendationStorage initialization"""
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table

        storage = RecommendationStorage(self.table_name)

        mock_boto3.resource.assert_called_once_with("dynamodb", region_name="us-east-1")
        mock_dynamodb.Table.assert_called_once_with(self.table_name)
        self.assertEqual(storage.table, mock_table)

    @patch("recommendation_storage.boto3")
    def test_store_recommendations(self, mock_boto3):
        """Test storing recommendations"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        storage = RecommendationStorage(self.table_name)

        # Mock recommendation
        rec = BetRecommendation(
            game_id="game123",
            sport="NBA",
            bet_type="moneyline",
            team_or_player="Lakers",
            market="Lakers ML",
            predicted_probability=0.65,
            confidence_score=0.8,
            expected_value=0.12,
            risk_level=RiskLevel.MODERATE,
            recommended_bet_amount=25.0,
            potential_payout=47.5,
            bookmaker="DraftKings",
            odds=-110,
            reasoning="Strong consensus pick",
        )

        # Mock clear existing recommendations
        mock_table.query.return_value = {"Items": []}

        storage.store_recommendations("NBA", "consensus", RiskLevel.MODERATE, [rec])

        # Verify put_item was called
        self.assertTrue(mock_table.put_item.called)
        call_args = mock_table.put_item.call_args[1]
        item = call_args["Item"]

        self.assertEqual(item["PK"], "RECOMMENDATIONS#NBA#consensus#moderate")
        self.assertTrue(item["SK"].startswith("REC#01#"))
        self.assertEqual(item["game_id"], "game123")
        self.assertEqual(item["rank"], 1)

    @patch("recommendation_storage.boto3")
    def test_get_recommendations(self, mock_boto3):
        """Test getting recommendations"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        # Mock query response
        mock_table.query.return_value = {
            "Items": [
                {
                    "PK": "RECOMMENDATIONS#NBA#consensus#moderate",
                    "SK": "REC#01#20260103T192000#game123",
                    "game_id": "game123",
                    "rank": 1,
                }
            ]
        }

        storage = RecommendationStorage(self.table_name)
        recommendations = storage.get_recommendations(
            "NBA", "consensus", RiskLevel.MODERATE, 10
        )

        # Verify query was called correctly
        mock_table.query.assert_called_once()
        call_args = mock_table.query.call_args[1]
        self.assertEqual(call_args["KeyConditionExpression"], "pk = :pk")
        self.assertEqual(
            call_args["ExpressionAttributeValues"][":pk"],
            "RECOMMENDATIONS#NBA#consensus#moderate",
        )
        self.assertEqual(call_args["Limit"], 10)

        # Verify results
        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["game_id"], "game123")

    @patch("recommendation_storage.boto3")
    def test_update_recommendation_outcome(self, mock_boto3):
        """Test updating recommendation outcome"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        storage = RecommendationStorage(self.table_name)
        storage.update_recommendation_outcome("PK123", "SK456", True, 0.15)

        # Verify update_item was called
        mock_table.update_item.assert_called_once()
        call_args = mock_table.update_item.call_args[1]

        self.assertEqual(call_args["Key"], {"PK": "PK123", "SK": "SK456"})
        self.assertIn("actual_outcome = :outcome", call_args["UpdateExpression"])
        self.assertEqual(call_args["ExpressionAttributeValues"][":outcome"], True)


if __name__ == "__main__":
    unittest.main()
