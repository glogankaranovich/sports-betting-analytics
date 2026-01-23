import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

os.environ["DYNAMODB_TABLE"] = "test-table"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis_generator import lambda_handler  # noqa: E402


class TestAnalysisGenerator(unittest.TestCase):
    @patch("analysis_generator.ModelFactory")
    @patch("analysis_generator.generate_game_analysis")
    def test_lambda_handler_games(self, mock_gen_game, mock_factory):
        """Test lambda handler for game analysis"""
        mock_model = Mock()
        mock_factory.create_model.return_value = mock_model
        mock_gen_game.return_value = 5

        event = {"sport": "basketball_nba", "model": "consensus", "bet_type": "games"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["analyses_count"], 5)
        mock_factory.create_model.assert_called_once_with("consensus")
        mock_gen_game.assert_called_once()

    @patch("analysis_generator.ModelFactory")
    @patch("analysis_generator.generate_prop_analysis")
    def test_lambda_handler_props(self, mock_gen_prop, mock_factory):
        """Test lambda handler for prop analysis"""
        mock_model = Mock()
        mock_factory.create_model.return_value = mock_model
        mock_gen_prop.return_value = 10

        event = {"sport": "basketball_nba", "model": "consensus", "bet_type": "props"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["analyses_count"], 10)
        mock_gen_prop.assert_called_once()

    @patch("analysis_generator.ModelFactory")
    @patch("analysis_generator.generate_game_analysis")
    @patch("analysis_generator.generate_prop_analysis")
    def test_lambda_handler_all(self, mock_gen_prop, mock_gen_game, mock_factory):
        """Test lambda handler for both game and prop analysis"""
        mock_model = Mock()
        mock_factory.create_model.return_value = mock_model
        mock_gen_game.return_value = 5
        mock_gen_prop.return_value = 10

        event = {"sport": "basketball_nba", "model": "consensus", "bet_type": "all"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertEqual(body["analyses_count"], 15)
        mock_gen_game.assert_called_once()
        mock_gen_prop.assert_called_once()

    @patch("analysis_generator.ModelFactory")
    def test_lambda_handler_error(self, mock_factory):
        """Test lambda handler error handling"""
        mock_factory.create_model.side_effect = Exception("Model error")

        event = {"sport": "basketball_nba", "model": "invalid"}
        result = lambda_handler(event, None)

        self.assertEqual(result["statusCode"], 500)
        body = json.loads(result["body"])
        self.assertIn("error", body)

    @patch("analysis_generator.ModelFactory")
    def test_lambda_handler_defaults(self, mock_factory):
        """Test lambda handler with default parameters"""
        mock_model = Mock()
        mock_factory.create_model.return_value = mock_model

        with patch("analysis_generator.generate_game_analysis", return_value=0):
            with patch("analysis_generator.generate_prop_analysis", return_value=0):
                event = {}
                result = lambda_handler(event, None)

                self.assertEqual(result["statusCode"], 200)
                # Should use defaults: basketball_nba, consensus, games
                mock_factory.create_model.assert_called_once_with("consensus")


if __name__ == "__main__":
    unittest.main()
