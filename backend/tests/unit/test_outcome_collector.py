import unittest
import sys
import os
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from outcome_collector import OutcomeCollector  # noqa: E402


class TestOutcomeCollector(unittest.TestCase):
    def setUp(self):
        self.table_name = "test-table"
        self.api_key = "test-key"

    @patch("outcome_collector.boto3")
    def test_init(self, mock_boto3):
        """Test OutcomeCollector initialization"""
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table

        collector = OutcomeCollector(self.table_name, self.api_key)

        mock_boto3.resource.assert_called_once_with("dynamodb", region_name="us-east-1")
        mock_dynamodb.Table.assert_called_once_with(self.table_name)
        self.assertEqual(collector.odds_api_key, self.api_key)

    def test_determine_winner(self):
        """Test determining game winner"""
        collector = OutcomeCollector(self.table_name, self.api_key)

        # Home team wins
        game1 = {"home_score": "120", "away_score": "115"}
        self.assertTrue(collector._determine_winner(game1))

        # Away team wins
        game2 = {"home_score": "100", "away_score": "105"}
        self.assertFalse(collector._determine_winner(game2))

        # Missing scores
        game3 = {"home_score": None, "away_score": "105"}
        self.assertFalse(collector._determine_winner(game3))

    def test_determine_bet_outcome(self):
        """Test determining bet outcome"""
        collector = OutcomeCollector(self.table_name, self.api_key)

        # Home team moneyline bet - home wins
        rec1 = {"bet_type": "moneyline", "team_or_player": "Lakers (Home)"}
        self.assertTrue(collector._determine_bet_outcome(rec1, True))

        # Home team moneyline bet - home loses
        self.assertFalse(collector._determine_bet_outcome(rec1, False))

        # Away team moneyline bet - away wins (home loses)
        rec2 = {"bet_type": "moneyline", "team_or_player": "Warriors"}
        self.assertTrue(collector._determine_bet_outcome(rec2, False))

    def test_calculate_roi(self):
        """Test ROI calculation"""
        collector = OutcomeCollector(self.table_name, self.api_key)

        # Winning bet
        rec1 = {"recommended_bet_amount": 100, "potential_payout": 150}
        roi_win = collector._calculate_roi(rec1, True)
        self.assertEqual(roi_win, 0.5)  # 50% profit

        # Losing bet
        roi_loss = collector._calculate_roi(rec1, False)
        self.assertEqual(roi_loss, -1.0)  # Lost entire bet

        # Zero bet amount
        rec2 = {"recommended_bet_amount": 0, "potential_payout": 150}
        roi_zero = collector._calculate_roi(rec2, True)
        self.assertEqual(roi_zero, 0.0)

    def test_map_sport_name(self):
        """Test sport name mapping - returns api_sport directly"""
        collector = OutcomeCollector(self.table_name, self.api_key)

        self.assertEqual(
            collector._map_sport_name("americanfootball_nfl"), "americanfootball_nfl"
        )
        self.assertEqual(collector._map_sport_name("basketball_nba"), "basketball_nba")
        self.assertEqual(collector._map_sport_name("unknown_sport"), "unknown_sport")

    @patch("outcome_collector.boto3")
    def test_update_analysis_outcomes(self, mock_boto3):
        """Test updating analysis outcomes with new schema"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table

        # Mock scan response with new schema
        mock_table.scan.return_value = {
            "Items": [
                {
                    "pk": "ANALYSIS#basketball_nba#game123#fanduel",
                    "sk": "consensus#game#LATEST",
                    "analysis_type": "game",
                    "prediction": "Lakers +2.5",
                    "game_id": "game123",
                }
            ]
        }

        collector = OutcomeCollector(self.table_name, self.api_key)
        game = {
            "id": "game123",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "120",
            "away_score": "115",
        }

        updates = collector._update_analysis_outcomes(game)

        # Verify scan and update were called
        mock_table.scan.assert_called_once()
        mock_table.update_item.assert_called_once()
        self.assertEqual(updates, 1)


if __name__ == "__main__":
    unittest.main()
