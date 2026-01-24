import os
import sys
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal

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


if __name__ == "__main__":
    unittest.main()
