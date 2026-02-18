"""
Extended unit tests for analysis_generator.py to increase coverage
"""
import unittest
from unittest.mock import patch, MagicMock, call
from decimal import Decimal
import json
import os

os.environ["TABLE_NAME"] = "test-table"

with patch("boto3.resource") as mock_resource:
    mock_dynamodb = MagicMock()
    mock_table = MagicMock()
    mock_dynamodb.Table.return_value = mock_table
    mock_resource.return_value = mock_dynamodb
    from analysis_generator import (
        lambda_handler,
        generate_game_analysis,
        generate_prop_analysis,
        store_analysis,
        decimal_to_float,
        float_to_decimal,
    )


class TestLambdaHandler(unittest.TestCase):
    """Test Lambda handler function"""

    @patch("analysis_generator.generate_game_analysis")
    @patch("analysis_generator.ModelFactory.create_model")
    def test_lambda_handler_games(self, mock_factory, mock_gen_game):
        """Test Lambda handler for game analysis"""
        mock_gen_game.return_value = 5
        mock_factory.return_value = MagicMock()

        event = {"sport": "basketball_nba", "model": "consensus", "bet_type": "games"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["analyses_count"], 5)
        self.assertEqual(body["sport"], "basketball_nba")
        mock_gen_game.assert_called_once()

    @patch("analysis_generator.generate_prop_analysis")
    @patch("analysis_generator.ModelFactory.create_model")
    def test_lambda_handler_props(self, mock_factory, mock_gen_prop):
        """Test Lambda handler for prop analysis"""
        mock_gen_prop.return_value = 3
        mock_factory.return_value = MagicMock()

        event = {"sport": "basketball_nba", "model": "consensus", "bet_type": "props"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["analyses_count"], 3)
        mock_gen_prop.assert_called_once()

    @patch("analysis_generator.generate_prop_analysis")
    @patch("analysis_generator.generate_game_analysis")
    @patch("analysis_generator.ModelFactory.create_model")
    def test_lambda_handler_both(self, mock_factory, mock_gen_game, mock_gen_prop):
        """Test Lambda handler for both games and props"""
        mock_gen_game.return_value = 5
        mock_gen_prop.return_value = 3
        mock_factory.return_value = MagicMock()

        event = {"sport": "basketball_nba", "model": "consensus", "bet_type": "both"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["analyses_count"], 8)

    @patch("analysis_generator.ModelFactory.create_model")
    def test_lambda_handler_error(self, mock_factory):
        """Test Lambda handler error handling"""
        mock_factory.side_effect = Exception("Model error")

        event = {"sport": "basketball_nba", "model": "invalid"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("error", body)

    @patch("analysis_generator.generate_game_analysis")
    @patch("analysis_generator.ModelFactory.create_model")
    def test_lambda_handler_with_limit(self, mock_factory, mock_gen_game):
        """Test Lambda handler with limit parameter"""
        mock_gen_game.return_value = 2
        mock_factory.return_value = MagicMock()

        event = {
            "sport": "basketball_nba",
            "model": "consensus",
            "bet_type": "games",
            "limit": 2,
        }
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        mock_gen_game.assert_called_once_with("basketball_nba", mock_factory.return_value, 2)


class TestStoreAnalysis(unittest.TestCase):
    """Test store_analysis function"""

    @patch("analysis_generator.table")
    def test_store_analysis_success(self, mock_table):
        """Test storing analysis item"""
        item = {
            "pk": "ANALYSIS#test",
            "sk": "consensus#game#LATEST",
            "confidence": Decimal("0.75"),
        }

        store_analysis(item)
        mock_table.put_item.assert_called_once_with(Item=item)

    @patch("analysis_generator.table")
    def test_store_analysis_with_inverse(self, mock_table):
        """Test storing analysis with inverse prediction"""
        item = {
            "pk": "ANALYSIS#test",
            "sk": "consensus#game#LATEST",
            "confidence": Decimal("0.75"),
            "inverse_prediction": {"confidence": Decimal("0.25")},
        }

        store_analysis(item)
        mock_table.put_item.assert_called_once()


class TestDecimalConversion(unittest.TestCase):
    """Test decimal conversion utilities"""

    def test_decimal_to_float(self):
        """Test converting Decimal to float"""
        obj = {"value": Decimal("0.75"), "nested": {"val": Decimal("1.5")}}
        result = decimal_to_float(obj)
        self.assertEqual(result["value"], 0.75)
        self.assertEqual(result["nested"]["val"], 1.5)

    def test_decimal_to_float_list(self):
        """Test converting list with Decimals"""
        obj = [Decimal("0.5"), Decimal("1.0")]
        result = decimal_to_float(obj)
        self.assertEqual(result, [0.5, 1.0])

    def test_float_to_decimal(self):
        """Test converting float to Decimal"""
        obj = {"value": 0.75, "nested": {"val": 1.5}}
        result = float_to_decimal(obj)
        self.assertEqual(result["value"], Decimal("0.75"))
        self.assertEqual(result["nested"]["val"], Decimal("1.5"))

    def test_float_to_decimal_list(self):
        """Test converting list with floats"""
        obj = [0.5, 1.0]
        result = float_to_decimal(obj)
        self.assertEqual(result, [Decimal("0.5"), Decimal("1.0")])


if __name__ == "__main__":
    unittest.main()
