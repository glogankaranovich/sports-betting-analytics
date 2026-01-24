import os
import sys
import unittest
from unittest.mock import Mock, patch
from decimal import Decimal

os.environ["DYNAMODB_TABLE"] = "test-table"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from player_stats_collector import PlayerStatsCollector  # noqa: E402


class TestPlayerStatsCollector(unittest.TestCase):
    def setUp(self):
        self.mock_table = Mock()

    @patch("player_stats_collector.boto3")
    def test_init(self, mock_boto3):
        mock_dynamodb = Mock()
        mock_boto3.resource.return_value = mock_dynamodb
        mock_dynamodb.Table.return_value = self.mock_table

        PlayerStatsCollector()

        mock_boto3.resource.assert_called_once()
        mock_dynamodb.Table.assert_called_once_with("test-table")

    @patch("player_stats_collector.boto3")
    @patch("player_stats_collector.requests")
    def test_fetch_espn_player_stats_success(self, mock_requests, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "boxscore": {
                "players": [
                    {
                        "team": {"displayName": "Test Team"},
                        "statistics": [
                            {
                                "athletes": [
                                    {
                                        "athlete": {"displayName": "Test Player"},
                                        "stats": ["30", "5-10", "2-5", "3-4", "2", "5"],
                                    }
                                ],
                                "labels": ["MIN", "FG", "3PT", "FT", "OREB", "DREB"],
                            }
                        ],
                    }
                ]
            }
        }
        mock_requests.get.return_value = mock_response

        collector = PlayerStatsCollector()
        stats = collector._fetch_espn_player_stats("401810482", "basketball_nba")

        self.assertIsInstance(stats, list)
        self.assertGreater(len(stats), 0)
        self.assertIn("player_name", stats[0])

    @patch("player_stats_collector.boto3")
    def test_store_player_stats(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        collector = PlayerStatsCollector()
        game_id = "test_game_123"
        player_stats = [
            {
                "player_name": "Test Player",
                "PTS": "25",
                "REB": "10",
                "AST": "5",
            }
        ]

        collector._store_player_stats(game_id, player_stats, "basketball_nba")

        self.mock_table.put_item.assert_called()
        call_args = self.mock_table.put_item.call_args[1]
        item = call_args["Item"]

        self.assertEqual(item["pk"], "PLAYER_STATS#basketball_nba#test_player")
        self.assertEqual(item["game_id"], game_id)
        self.assertEqual(item["game_index_pk"], game_id)
        self.assertEqual(
            item["game_index_sk"], "PLAYER_STATS#basketball_nba#test_player"
        )
        self.assertEqual(item["sport"], "basketball_nba")
        self.assertEqual(item["player_name"], "Test Player")
        self.assertIn("sk", item)  # SK is timestamp
        self.assertIn("collected_at", item)  # collected_at is timestamp

    @patch("player_stats_collector.boto3")
    def test_convert_to_decimal(self, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        collector = PlayerStatsCollector()

        result = collector._convert_to_decimal(3.14)
        self.assertIsInstance(result, Decimal)
        self.assertEqual(result, Decimal("3.14"))

        result = collector._convert_to_decimal({"score": 25.5, "name": "test"})
        self.assertIsInstance(result["score"], Decimal)
        self.assertEqual(result["name"], "test")

        result = collector._convert_to_decimal([1.5, 2.5, "text"])
        self.assertIsInstance(result[0], Decimal)
        self.assertEqual(result[2], "text")

    @patch("player_stats_collector.boto3")
    @patch("player_stats_collector.requests")
    def test_fetch_espn_player_stats_api_error(self, mock_requests, mock_boto3):
        mock_boto3.resource.return_value.Table.return_value = self.mock_table

        mock_response = Mock()
        mock_response.status_code = 404
        mock_requests.get.return_value = mock_response

        collector = PlayerStatsCollector()
        stats = collector._fetch_espn_player_stats("invalid_id", "basketball_nba")

        self.assertEqual(stats, [])


if __name__ == "__main__":
    unittest.main()
