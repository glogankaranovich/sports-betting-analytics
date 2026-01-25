import unittest
import sys
import os
from unittest.mock import Mock, patch
from decimal import Decimal

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

    @patch("outcome_collector.boto3")
    def test_store_outcome(self, mock_boto3):
        """Test storing game outcome with H2H indexing"""
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table

        collector = OutcomeCollector(self.table_name, self.api_key)

        game = {
            "id": "game123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Celtics",
            "home_score": 112,
            "away_score": 108,
            "completed_at": "2026-01-25T10:00:00Z",
        }

        collector._store_outcome(game)

        # Verify put_item was called
        mock_table.put_item.assert_called_once()
        call_args = mock_table.put_item.call_args[1]
        item = call_args["Item"]

        # Check basic fields
        self.assertEqual(item["pk"], "OUTCOME#basketball_nba#game123")
        self.assertEqual(item["sk"], "RESULT")
        self.assertEqual(item["winner"], "Lakers")
        self.assertEqual(item["home_score"], Decimal("112"))
        self.assertEqual(item["away_score"], Decimal("108"))

        # Check H2H fields (teams sorted alphabetically)
        self.assertEqual(item["h2h_pk"], "H2H#basketball_nba#celtics#lakers")
        self.assertEqual(item["h2h_sk"], "2026-01-25T10:00:00Z")

    @patch("outcome_collector.boto3")
    def test_store_prop_outcomes(self, mock_boto3):
        """Test storing prop outcomes from player stats"""
        mock_dynamodb = Mock()
        mock_table = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = mock_table

        # Mock player stats query
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "PLAYER_STATS#basketball_nba#lebron_james",
                    "player_name": "LeBron James",
                    "stats": {"PTS": 28, "REB": 10, "AST": 8, "3PM": 2},
                }
            ]
        }

        collector = OutcomeCollector(self.table_name, self.api_key)

        game = {
            "id": "game123",
            "sport": "basketball_nba",
            "completed_at": "2026-01-25T10:00:00Z",
        }

        count = collector._store_prop_outcomes(game)

        # Should store 4 prop outcomes (points, rebounds, assists, threes)
        self.assertEqual(count, 4)
        self.assertEqual(mock_table.put_item.call_count, 4)

        # Check one of the stored items
        first_call = mock_table.put_item.call_args_list[0][1]
        item = first_call["Item"]
        self.assertEqual(item["pk"], "PROP_OUTCOME#basketball_nba#game123#lebron_james")
        self.assertIn("RESULT#", item["sk"])
        self.assertEqual(item["player_name"], "LeBron James")

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
