import os
import sys
import unittest
from decimal import Decimal
from unittest.mock import Mock, MagicMock, patch

os.environ["DYNAMODB_TABLE"] = "test-table"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from team_stats_collector import TeamStatsCollector  # noqa: E402


class TestTeamStatsCollector(unittest.TestCase):
    def setUp(self):
        self.mock_table = Mock()

    @patch("team_stats_collector.boto3")
    def test_init(self, mock_boto3):
        mock_dynamodb = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = self.mock_table

        TeamStatsCollector()

        mock_boto3.resource.assert_called_once()
        mock_dynamodb.Table.assert_called_once_with("test-table")

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_fetch_espn_team_stats_success(self, mock_requests, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "boxscore": {
                "teams": [
                    {
                        "team": {"displayName": "Test Team"},
                        "statistics": [
                            {"label": "Field Goal %", "displayValue": "45.5"},
                            {"label": "3-Point %", "displayValue": "35.0"},
                        ],
                    }
                ]
            }
        }
        mock_requests.get.return_value = mock_response

        collector = TeamStatsCollector()
        stats = collector._fetch_espn_team_stats("401810482", "basketball_nba")

        self.assertIsInstance(stats, dict)
        self.assertIn("Test Team", stats)

    @patch("team_stats_collector.boto3")
    def test_store_team_stats(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        collector = TeamStatsCollector()
        game_id = "test_game_123"
        team_stats = {
            "Test Team": {
                "Field Goal %": "45.5",
                "3-Point %": "35.0",
            }
        }

        collector._store_team_stats(game_id, team_stats, "basketball_nba")

        self.mock_table.put_item.assert_called()
        call_args = self.mock_table.put_item.call_args[1]
        item = call_args["Item"]

        self.assertEqual(item["pk"], "TEAM_STATS#basketball_nba#test_team")
        self.assertEqual(item["game_id"], game_id)
        self.assertEqual(item["game_index_pk"], game_id)
        self.assertEqual(item["game_index_sk"], "TEAM_STATS#basketball_nba#test_team")
        self.assertEqual(item["sport"], "basketball_nba")
        self.assertEqual(item["team_name"], "Test Team")
        self.assertIn("sk", item)  # SK is timestamp
        self.assertIn("collected_at", item)  # collected_at is timestamp

    @patch("team_stats_collector.boto3")
    def test_convert_to_decimal(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        collector = TeamStatsCollector()

        result = collector._convert_to_decimal(3.14)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("3.14"))

        result = collector._convert_to_decimal({"score": 25.5, "name": "test"})
        self.assertIsInstance(result["score"], Decimal)
        self.assertEqual(result["name"], "test")

    @patch("team_stats_collector.boto3")
    def test_supported_sports(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        collector = TeamStatsCollector()

        # Test supported sports
        self.assertEqual(collector.collect_stats_for_sport("basketball_nba"), 0)
        self.assertEqual(collector.collect_stats_for_sport("americanfootball_nfl"), 0)
        self.assertEqual(collector.collect_stats_for_sport("baseball_mlb"), 0)
        self.assertEqual(collector.collect_stats_for_sport("icehockey_nhl"), 0)
        self.assertEqual(collector.collect_stats_for_sport("soccer_epl"), 0)

        # Test unsupported sport
        self.assertEqual(collector.collect_stats_for_sport("unsupported_sport"), 0)

    @patch("team_stats_collector.boto3")
    def test_get_completed_games(self, mock_boto3):
        """Test getting completed games"""
        mock_boto3.resource.return_value.Table.return_value = self.mock_table
        
        self.mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "commence_time": "2026-01-01T19:00:00Z"
                }
            ]
        }

        collector = TeamStatsCollector()
        games = collector._get_completed_games("basketball_nba")

        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "game123")

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_fetch_espn_team_stats_api_error(self, mock_requests, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = Exception("Not found")
        mock_requests.get.return_value = mock_response

        collector = TeamStatsCollector()
        stats = collector._fetch_espn_team_stats("invalid_id", "basketball_nba")

        self.assertIsNone(stats)

    @patch("team_stats_collector.TeamStatsCollector")
    @patch("team_stats_collector.boto3")
    def test_lambda_handler(self, mock_boto3, mock_collector_class):
        """Test lambda handler"""
        mock_collector = MagicMock()
        mock_collector.collect_stats_for_sport.return_value = 30
        mock_collector_class.return_value = mock_collector

        from team_stats_collector import lambda_handler
        result = lambda_handler({}, {})

        self.assertEqual(result["statusCode"], 200)
        self.assertIn("games_processed", result["body"])


if __name__ == "__main__":
    unittest.main()


class TestTeamStatsCollectorAdditional(unittest.TestCase):
    """Additional tests for team stats collector"""
    
    def setUp(self):
        self.mock_table = Mock()

    @patch("team_stats_collector.boto3")
    def test_all_sports_supported(self, mock_boto3):
        """Test all 10 sports are in SPORT_MAP"""
        expected_sports = [
            "basketball_nba", "basketball_wnba", "basketball_ncaab", "basketball_wncaab",
            "americanfootball_nfl", "americanfootball_ncaaf",
            "baseball_mlb", "icehockey_nhl", "soccer_epl", "soccer_usa_mls"
        ]
        for sport in expected_sports:
            self.assertIn(sport, TeamStatsCollector.SPORT_MAP)

    @patch("team_stats_collector.boto3")
    def test_extract_numeric_valid(self, mock_boto3):
        """Test extracting numeric values"""
        mock_boto3.resource.return_value.Table.return_value = self.mock_table
        collector = TeamStatsCollector()
        
        self.assertEqual(collector._extract_numeric("45.5"), 45.5)
        self.assertEqual(collector._extract_numeric("1,234.56"), 1234.56)
        self.assertEqual(collector._extract_numeric("75%"), 75.0)
        self.assertEqual(collector._extract_numeric("100"), 100.0)

    @patch("team_stats_collector.boto3")
    def test_extract_numeric_invalid(self, mock_boto3):
        """Test extracting numeric from invalid values"""
        mock_boto3.resource.return_value.Table.return_value = self.mock_table
        collector = TeamStatsCollector()
        
        self.assertEqual(collector._extract_numeric("invalid"), 0.0)
        self.assertEqual(collector._extract_numeric(None), 0.0)
        self.assertEqual(collector._extract_numeric(""), 0.0)

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_find_espn_game_id_success(self, mock_requests, mock_boto3):
        """Test finding ESPN game ID"""
        mock_boto3.resource.return_value.Table.return_value = self.mock_table
        
        mock_response = Mock()
        mock_response.json.return_value = {
            "events": [
                {
                    "id": "401810482",
                    "competitions": [
                        {
                            "competitors": [
                                {"team": {"displayName": "Lakers"}},
                                {"team": {"displayName": "Warriors"}}
                            ]
                        }
                    ]
                }
            ]
        }
        mock_requests.get.return_value = mock_response
        
        collector = TeamStatsCollector()
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-01-25T19:00:00Z"
        }
        
        espn_id = collector._find_espn_game_id(game, "basketball_nba")
        self.assertEqual(espn_id, "401810482")

    @patch("team_stats_collector.boto3")
    @patch("team_stats_collector.requests")
    def test_find_espn_game_id_not_found(self, mock_requests, mock_boto3):
        """Test when ESPN game ID is not found"""
        mock_boto3.resource.return_value.Table.return_value = self.mock_table
        
        mock_response = Mock()
        mock_response.json.return_value = {"events": []}
        mock_requests.get.return_value = mock_response
        
        collector = TeamStatsCollector()
        game = {
            "home_team": "Team A",
            "away_team": "Team B",
            "commence_time": "2026-01-25T19:00:00Z"
        }
        
        espn_id = collector._find_espn_game_id(game, "basketball_nba")
        self.assertIsNone(espn_id)

    @patch("team_stats_collector.boto3")
    def test_find_espn_game_id_unsupported_sport(self, mock_boto3):
        """Test finding game ID for unsupported sport"""
        mock_boto3.resource.return_value.Table.return_value = self.mock_table
        
        collector = TeamStatsCollector()
        game = {
            "home_team": "Team A",
            "away_team": "Team B",
            "commence_time": "2026-01-25T19:00:00Z"
        }
        
        espn_id = collector._find_espn_game_id(game, "unsupported_sport")
        self.assertIsNone(espn_id)

    @patch("team_stats_collector.boto3")
    def test_fetch_espn_team_stats_unsupported_sport(self, mock_boto3):
        """Test fetching stats for unsupported sport"""
        mock_boto3.resource.return_value.Table.return_value = self.mock_table
        
        collector = TeamStatsCollector()
        stats = collector._fetch_espn_team_stats("game123", "unsupported_sport")
        self.assertIsNone(stats)

    @patch("team_stats_collector.boto3")
    def test_store_adjusted_metrics(self, mock_boto3):
        """Test storing adjusted metrics"""
        mock_boto3.resource.return_value.Table.return_value = self.mock_table
        
        collector = TeamStatsCollector()
        metrics = {
            "adjusted_ppg": 115.5,
            "fg_pct": 47.5,
            "games_analyzed": 10
        }
        
        collector._store_adjusted_metrics("Los Angeles Lakers", metrics, "basketball_nba")
        
        self.mock_table.put_item.assert_called()
        call_args = self.mock_table.put_item.call_args[1]["Item"]
        self.assertEqual(call_args["pk"], "ADJUSTED_METRICS#basketball_nba#los_angeles_lakers")
        self.assertEqual(call_args["sport"], "basketball_nba")
        self.assertEqual(call_args["team_name"], "Los Angeles Lakers")
        self.assertTrue(call_args["latest"])


if __name__ == "__main__":
    unittest.main()
