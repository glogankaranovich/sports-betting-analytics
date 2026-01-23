import unittest
from unittest.mock import Mock, patch
import json
from decimal import Decimal
from odds_collector import (
    OddsCollector,
    convert_floats_to_decimal,
    lambda_handler,
    get_secret,
)


class TestOddsCollector(unittest.TestCase):
    def setUp(self):
        self.mock_table = Mock()

    @patch("odds_collector.boto3.resource")
    @patch("odds_collector.get_secret")
    def test_init_with_secret_arn(self, mock_get_secret, mock_boto3):
        mock_get_secret.return_value = "test-api-key"
        mock_boto3.return_value.Table.return_value = self.mock_table

        with patch.dict(
            "os.environ",
            {
                "ODDS_API_SECRET_ARN": "arn:aws:secretsmanager:us-east-1:123:secret:test",
                "DYNAMODB_TABLE": "test-table",
            },
        ):
            collector = OddsCollector()

        self.assertEqual(collector.api_key, "test-api-key")
        mock_get_secret.assert_called_once_with(
            "arn:aws:secretsmanager:us-east-1:123:secret:test"
        )

    @patch("odds_collector.boto3.resource")
    def test_init_with_env_key(self, mock_boto3):
        mock_boto3.return_value.Table.return_value = self.mock_table

        with patch.dict(
            "os.environ",
            {"ODDS_API_KEY": "env-api-key", "DYNAMODB_TABLE": "test-table"},
        ):
            collector = OddsCollector()

        self.assertEqual(collector.api_key, "env-api-key")

    def test_convert_floats_to_decimal(self):
        test_data = {
            "price": 1.5,
            "point": -3.0,
            "nested": {"value": 2.5, "list": [1.1, 2.2, "string"]},
        }

        result = convert_floats_to_decimal(test_data)

        self.assertEqual(result["price"], Decimal("1.5"))
        self.assertEqual(result["point"], Decimal("-3.0"))
        self.assertEqual(result["nested"]["value"], Decimal("2.5"))
        self.assertEqual(result["nested"]["list"][0], Decimal("1.1"))
        self.assertEqual(result["nested"]["list"][2], "string")

    @patch("odds_collector.requests.get")
    @patch("odds_collector.boto3.resource")
    def test_get_active_sports(self, mock_boto3, mock_requests):
        mock_boto3.return_value.Table.return_value = self.mock_table
        mock_response = Mock()
        mock_response.json.return_value = [
            {"key": "americanfootball_nfl", "active": True},
            {"key": "basketball_nba", "active": True},
            {"key": "soccer_epl", "active": True},
            {"key": "baseball_mlb", "active": False},
        ]
        mock_requests.return_value = mock_response

        with patch.dict(
            "os.environ", {"ODDS_API_KEY": "test-key", "DYNAMODB_TABLE": "test-table"}
        ):
            collector = OddsCollector()
            result = collector.get_active_sports()

        self.assertEqual(
            result, ["americanfootball_nfl", "basketball_nba", "soccer_epl"]
        )

    @patch("odds_collector.requests.get")
    @patch("odds_collector.boto3.resource")
    def test_get_odds(self, mock_boto3, mock_requests):
        mock_boto3.return_value.Table.return_value = self.mock_table
        mock_response = Mock()
        mock_response.json.return_value = [{"id": "game1", "home_team": "Team A"}]
        mock_requests.return_value = mock_response

        with patch.dict(
            "os.environ", {"ODDS_API_KEY": "test-key", "DYNAMODB_TABLE": "test-table"}
        ):
            collector = OddsCollector()
            result = collector.get_odds("americanfootball_nfl")

        self.assertEqual(result, [{"id": "game1", "home_team": "Team A"}])

    @patch("odds_collector.boto3.resource")
    def test_store_odds(self, mock_boto3):
        mock_boto3.return_value.Table.return_value = self.mock_table

        odds_data = [
            {
                "id": "game1",
                "home_team": "Team A",
                "away_team": "Team B",
                "commence_time": "2025-01-01T12:00:00Z",
                "bookmakers": [
                    {
                        "key": "betmgm",
                        "markets": [{"key": "h2h", "outcomes": [{"price": 1.5}]}],
                    }
                ],
            }
        ]

        with patch.dict(
            "os.environ", {"ODDS_API_KEY": "test-key", "DYNAMODB_TABLE": "test-table"}
        ):
            collector = OddsCollector()
            collector.store_odds("americanfootball_nfl", odds_data)

        self.mock_table.put_item.assert_called()
        # Check that put_item was called with the correct data structure
        call_args = self.mock_table.put_item.call_args_list
        self.assertGreater(len(call_args), 0)  # At least one put_item call

        # Check that the game data was stored
        found_game_record = False
        for call in call_args:
            item = call[1]["Item"]  # Get the Item from kwargs
            if item["pk"] == "GAME#game1" and "betmgm#h2h#LATEST" in item["sk"]:
                found_game_record = True
                self.assertEqual(item["sport"], "americanfootball_nfl")
                break

        self.assertTrue(found_game_record, "Game record not found in put_item calls")


class TestLambdaHandler(unittest.TestCase):
    @patch("odds_collector.OddsCollector")
    def test_lambda_handler_success(self, mock_collector_class):
        mock_collector = Mock()
        mock_collector.collect_odds_for_sport.return_value = ["game1", "game2", "game3"]
        mock_collector_class.return_value = mock_collector

        result = lambda_handler({"sport": "basketball_nba"}, {})

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("Successfully collected odds", body["message"])
        self.assertEqual(body["games_collected"], 3)

    @patch("odds_collector.OddsCollector")
    def test_lambda_handler_error(self, mock_collector_class):
        mock_collector_class.side_effect = Exception("Test error")

        result = lambda_handler({"sport": "basketball_nba"}, {})

        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertEqual(body["error"], "Test error")


class TestGetSecret(unittest.TestCase):
    @patch("odds_collector.boto3.client")
    def test_get_secret(self, mock_boto3_client):
        mock_client = Mock()
        mock_client.get_secret_value.return_value = {"SecretString": "secret-value"}
        mock_boto3_client.return_value = mock_client

        result = get_secret("arn:aws:secretsmanager:us-east-1:123:secret:test")

        self.assertEqual(result, "secret-value")
        mock_client.get_secret_value.assert_called_once_with(
            SecretId="arn:aws:secretsmanager:us-east-1:123:secret:test"
        )


if __name__ == "__main__":
    unittest.main()
