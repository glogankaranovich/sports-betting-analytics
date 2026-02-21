"""
Comprehensive tests for outcome collector
"""
import os
import unittest
from unittest.mock import Mock, patch
from datetime import datetime

os.environ["DYNAMODB_TABLE"] = "test-table"

from outcome_collector import OutcomeCollector


class TestOutcomeCollectorComprehensive(unittest.TestCase):

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    @patch("outcome_collector.requests")
    def test_collect_recent_outcomes_full_workflow(self, mock_requests, mock_boto3, mock_elo):
        """Test full outcome collection workflow"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock API response with completed game
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "game123",
                "completed": True,
                "home_team": "Lakers",
                "away_team": "Warriors",
                "scores": [{"score": 110}, {"score": 105}],
                "last_update": "2026-02-21T22:00:00Z"
            }
        ]
        mock_requests.get.return_value = mock_response
        
        # Mock table queries for analysis updates
        mock_table.query.return_value = {"Items": []}
        
        collector = OutcomeCollector("test-table", "test-key")
        results = collector.collect_recent_outcomes(days_back=1)
        
        self.assertIn("stored_outcomes", results)
        self.assertIn("updated_elo", results)
        self.assertIn("stored_prop_outcomes", results)
        self.assertIn("updated_analysis", results)

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    @patch("outcome_collector.requests")
    def test_get_completed_games_filters_completed(self, mock_requests, mock_boto3, mock_elo):
        """Test getting only completed games"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "id": "game1",
                "completed": True,
                "home_team": "Lakers",
                "away_team": "Warriors",
                "scores": [{"score": 110}, {"score": 105}]
            },
            {
                "id": "game2",
                "completed": False,  # Not completed
                "home_team": "Celtics",
                "away_team": "Heat"
            }
        ]
        mock_requests.get.return_value = mock_response
        
        collector = OutcomeCollector("test-table", "test-key")
        games = collector._get_completed_games(days_back=1)
        
        # Should only return completed games (1 per sport, 5 sports)
        self.assertGreater(len(games), 0)
        # All should be completed
        for game in games:
            self.assertIn("id", game)

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    def test_update_elo_ratings_success(self, mock_boto3, mock_elo_class):
        """Test successful Elo rating update"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        mock_elo = Mock()
        mock_elo_class.return_value = mock_elo
        
        collector = OutcomeCollector("test-table", "test-key")
        
        game = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": 110,
            "away_score": 105
        }
        
        result = collector._update_elo_ratings(game)
        
        self.assertTrue(result)
        mock_elo.update_ratings.assert_called_once_with(
            "basketball_nba", "Lakers", "Warriors", 110, 105
        )

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    def test_update_elo_ratings_missing_data(self, mock_boto3, mock_elo):
        """Test Elo update with missing data"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        collector = OutcomeCollector("test-table", "test-key")
        
        game = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            # Missing away_team and scores
        }
        
        result = collector._update_elo_ratings(game)
        self.assertFalse(result)

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    def test_store_outcome_creates_records(self, mock_boto3, mock_elo):
        """Test storing outcome creates proper DynamoDB records"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        collector = OutcomeCollector("test-table", "test-key")
        
        game = {
            "id": "game123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": 110,
            "away_score": 105,
            "completed_at": "2026-02-21T22:00:00Z"
        }
        
        collector._store_outcome(game)
        
        # Should call put_item at least once
        self.assertGreater(mock_table.put_item.call_count, 0)
        
        # Check first call has correct structure
        call_args = mock_table.put_item.call_args_list[0][1]
        item = call_args["Item"]
        
        self.assertEqual(item["game_id"], "game123")
        self.assertEqual(item["sport"], "basketball_nba")
        self.assertEqual(item["winner"], "Lakers")

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    def test_store_outcome_h2h_key_sorted(self, mock_boto3, mock_elo):
        """Test H2H key is alphabetically sorted"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        collector = OutcomeCollector("test-table", "test-key")
        
        game = {
            "id": "game123",
            "sport": "basketball_nba",
            "home_team": "Warriors",  # W comes after L
            "away_team": "Lakers",
            "home_score": 105,
            "away_score": 110,
            "completed_at": "2026-02-21T22:00:00Z"
        }
        
        collector._store_outcome(game)
        
        call_args = mock_table.put_item.call_args_list[0][1]
        item = call_args["Item"]
        
        # H2H key should have teams in alphabetical order
        self.assertIn("lakers", item["h2h_pk"])
        self.assertIn("warriors", item["h2h_pk"])

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    def test_update_analysis_outcomes(self, mock_boto3, mock_elo):
        """Test updating analysis with outcomes"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock analysis query
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "ANALYSIS#game123",
                    "sk": "consensus#LATEST",
                    "prediction": "Lakers",
                    "confidence": 0.75
                }
            ]
        }
        
        collector = OutcomeCollector("test-table", "test-key")
        
        game = {
            "id": "game123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": 110,
            "away_score": 105
        }
        
        count = collector._update_analysis_outcomes(game)
        
        self.assertIsInstance(count, int)

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    def test_store_prop_outcomes(self, mock_boto3, mock_elo):
        """Test storing prop outcomes"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        # Mock prop query
        mock_table.query.return_value = {"Items": []}
        
        collector = OutcomeCollector("test-table", "test-key")
        
        game = {
            "id": "game123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors"
        }
        
        count = collector._store_prop_outcomes(game)
        
        self.assertIsInstance(count, int)

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    @patch("outcome_collector.requests")
    def test_collect_outcomes_handles_api_error(self, mock_requests, mock_boto3, mock_elo):
        """Test handling API errors gracefully"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        mock_requests.get.side_effect = Exception("API Error")
        
        collector = OutcomeCollector("test-table", "test-key")
        results = collector.collect_recent_outcomes(days_back=1)
        
        # Should return empty results without crashing
        self.assertEqual(results["stored_outcomes"], 0)

    @patch("outcome_collector.EloCalculator")
    @patch("outcome_collector.boto3")
    def test_map_sport_name(self, mock_boto3, mock_elo):
        """Test sport name mapping"""
        mock_table = Mock()
        mock_boto3.resource.return_value.Table.return_value = mock_table
        
        collector = OutcomeCollector("test-table", "test-key")
        
        # Test various sport mappings
        self.assertEqual(collector._map_sport_name("basketball_nba"), "basketball_nba")
        self.assertEqual(collector._map_sport_name("americanfootball_nfl"), "americanfootball_nfl")


if __name__ == "__main__":
    unittest.main()
