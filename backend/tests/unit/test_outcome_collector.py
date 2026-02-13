import os
import sys
import unittest
from decimal import Decimal
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

        # Verify put_item was called 3 times (outcome + 2 team outcomes)
        assert mock_table.put_item.call_count == 3
        
        # Check the main outcome record (first call)
        first_call = mock_table.put_item.call_args_list[0][1]
        item = first_call["Item"]

        # Check basic fields
        self.assertEqual(item["pk"], "OUTCOME#basketball_nba#game123")
        self.assertEqual(item["sk"], "RESULT")
        self.assertEqual(item["winner"], "Lakers")
        self.assertEqual(item["home_score"], Decimal("112"))
        self.assertEqual(item["away_score"], Decimal("108"))

        # Check H2H fields (teams sorted alphabetically)
        self.assertEqual(item["h2h_pk"], "H2H#basketball_nba#celtics#lakers")
        self.assertEqual(item["h2h_sk"], "2026-01-25T10:00:00Z")
        
        # Check team outcome records (second and third calls)
        lakers_call = mock_table.put_item.call_args_list[1][1]
        lakers_item = lakers_call["Item"]
        self.assertEqual(lakers_item["pk"], "TEAM_OUTCOME#basketball_nba#lakers")
        self.assertEqual(lakers_item["team"], "Lakers")
        self.assertEqual(lakers_item["is_home"], True)
        
        celtics_call = mock_table.put_item.call_args_list[2][1]
        celtics_item = celtics_call["Item"]
        self.assertEqual(celtics_item["pk"], "TEAM_OUTCOME#basketball_nba#celtics")
        self.assertEqual(celtics_item["team"], "Celtics")
        self.assertEqual(celtics_item["is_home"], False)

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

        # Mock query to return item only for consensus/game combination
        def mock_query(**kwargs):
            pk = kwargs.get("ExpressionAttributeValues", {}).get(":pk", "")
            if "consensus" in pk and "game" in pk:
                return {
                    "Items": [
                        {
                            "pk": "ANALYSIS#basketball_nba#fanduel#consensus#game",
                            "sk": "LATEST",
                            "analysis_type": "game",
                            "prediction": "Lakers +2.5",
                            "game_id": "game123",
                        }
                    ]
                }
            return {"Items": []}

        mock_table.query.side_effect = mock_query

        collector = OutcomeCollector(self.table_name, self.api_key)
        game = {
            "id": "game123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "120",
            "away_score": "115",
        }

        updates = collector._update_analysis_outcomes(game)

        # Verify query and update were called
        self.assertGreater(mock_table.query.call_count, 0)
        self.assertEqual(mock_table.update_item.call_count, 1)
        self.assertEqual(updates, 1)


if __name__ == "__main__":
    unittest.main()
