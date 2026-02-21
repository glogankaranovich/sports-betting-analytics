"""
Comprehensive tests for analysis generator
"""
import os
import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

os.environ["DYNAMODB_TABLE"] = "test-table"

from analysis_generator import (
    lambda_handler,
    generate_game_analysis,
    generate_prop_analysis,
    store_analysis,
    create_inverse_prediction
)


class TestAnalysisGeneratorComprehensive(unittest.TestCase):

    @patch("analysis_generator.generate_game_analysis")
    @patch("analysis_generator.generate_prop_analysis")
    @patch("analysis_generator.ModelFactory")
    def test_lambda_handler_games_only(self, mock_factory, mock_prop, mock_game):
        """Test lambda handler for games only"""
        mock_model = Mock()
        mock_factory.create_model.return_value = mock_model
        mock_game.return_value = 5
        
        event = {
            "sport": "basketball_nba",
            "model": "consensus",
            "bet_type": "games",
            "limit": 10
        }
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result["statusCode"], 200)
        mock_game.assert_called_once()
        mock_prop.assert_not_called()

    @patch("analysis_generator.generate_game_analysis")
    @patch("analysis_generator.generate_prop_analysis")
    @patch("analysis_generator.ModelFactory")
    def test_lambda_handler_props_only(self, mock_factory, mock_prop, mock_game):
        """Test lambda handler for props only"""
        mock_model = Mock()
        mock_factory.create_model.return_value = mock_model
        mock_prop.return_value = 3
        
        event = {
            "sport": "basketball_nba",
            "model": "value",
            "bet_type": "props"
        }
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result["statusCode"], 200)
        mock_prop.assert_called_once()
        mock_game.assert_not_called()

    @patch("analysis_generator.generate_game_analysis")
    @patch("analysis_generator.generate_prop_analysis")
    @patch("analysis_generator.ModelFactory")
    def test_lambda_handler_both(self, mock_factory, mock_prop, mock_game):
        """Test lambda handler for both games and props"""
        mock_model = Mock()
        mock_factory.create_model.return_value = mock_model
        mock_game.return_value = 5
        mock_prop.return_value = 3
        
        event = {
            "sport": "basketball_nba",
            "model": "consensus",
            "bet_type": "all"
        }
        
        result = lambda_handler(event, None)
        
        self.assertEqual(result["statusCode"], 200)
        mock_game.assert_called_once()
        mock_prop.assert_called_once()

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
                mock_factory.create_model.assert_called_with("consensus")

    @patch("analysis_generator.ModelFactory")
    def test_lambda_handler_error(self, mock_factory):
        """Test lambda handler error handling"""
        mock_factory.create_model.side_effect = Exception("Model error")
        
        event = {"sport": "basketball_nba"}
        result = lambda_handler(event, None)
        
        self.assertEqual(result["statusCode"], 500)

    @patch("analysis_generator.DynamicModelWeighting")
    @patch("analysis_generator.table")
    def test_generate_game_analysis_with_games(self, mock_table, mock_weighting_class):
        """Test generating game analysis with actual games"""
        mock_weighting = Mock()
        mock_weighting.calculate_adjusted_confidence.return_value = 0.70
        mock_weighting_class.return_value = mock_weighting
        
        # Mock games query
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "bookmaker": "draftkings",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "sport": "basketball_nba",
                    "commence_time": (datetime.utcnow() + timedelta(hours=2)).isoformat(),
                    "latest": True,
                    "market_key": "h2h",
                    "outcomes": [
                        {"name": "Lakers", "price": -110},
                        {"name": "Warriors", "price": -110}
                    ]
                }
            ]
        }
        
        mock_model = Mock()
        mock_model.analyze_game_odds.return_value = None
        
        count = generate_game_analysis("basketball_nba", mock_model, limit=1)
        
        self.assertIsInstance(count, int)

    @patch("analysis_generator.DynamicModelWeighting")
    @patch("analysis_generator.table")
    def test_generate_game_analysis_pagination(self, mock_table, mock_weighting_class):
        """Test game analysis handles pagination"""
        mock_weighting = Mock()
        mock_weighting.calculate_adjusted_confidence.return_value = 0.70
        mock_weighting_class.return_value = mock_weighting
        
        # Mock paginated response
        mock_table.query.side_effect = [
            {
                "Items": [
                    {
                        "pk": "GAME#game1",
                        "bookmaker": "draftkings",
                        "home_team": "Lakers",
                        "away_team": "Warriors",
                        "sport": "basketball_nba",
                        "latest": True
                    }
                ],
                "LastEvaluatedKey": {"pk": "GAME#game1"}
            },
            {
                "Items": [],
                "LastEvaluatedKey": None
            }
        ]
        
        mock_model = Mock()
        mock_model.analyze_game_odds.return_value = None
        
        count = generate_game_analysis("basketball_nba", mock_model)
        
        self.assertIsInstance(count, int)

    @patch("analysis_generator.DynamicModelWeighting")
    @patch("analysis_generator.table")
    def test_generate_prop_analysis_with_props(self, mock_table, mock_weighting_class):
        """Test generating prop analysis"""
        mock_weighting = Mock()
        mock_weighting.calculate_adjusted_confidence.return_value = 0.65
        mock_weighting_class.return_value = mock_weighting
        
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "PROP#prop123",
                    "player_name": "LeBron James",
                    "market_key": "player_points",
                    "sport": "basketball_nba",
                    "point": 25.5,
                    "outcomes": [
                        {"name": "Over", "price": -110},
                        {"name": "Under", "price": -110}
                    ]
                }
            ]
        }
        
        mock_model = Mock()
        mock_model.analyze_player_prop.return_value = None
        
        count = generate_prop_analysis("basketball_nba", mock_model, limit=1)
        
        self.assertIsInstance(count, int)

    @patch("analysis_generator.table")
    def test_store_analysis_creates_record(self, mock_table):
        """Test storing analysis creates DynamoDB record"""
        analysis_dict = {
            "pk": "ANALYSIS#game123",
            "sk": "consensus#LATEST",
            "prediction": "Lakers",
            "confidence": 0.75
        }
        
        store_analysis(analysis_dict)
        
        mock_table.put_item.assert_called_once()

    def test_create_inverse_prediction_game(self):
        """Test creating inverse prediction for game"""
        analysis = {
            "pk": "ANALYSIS#game123",
            "sk": "consensus#LATEST",
            "prediction": "Lakers",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "confidence": 0.65,
            "analysis_type": "game"
        }
        
        inverse = create_inverse_prediction(analysis)
        
        self.assertIsNotNone(inverse)
        self.assertEqual(inverse["sk"], "consensus#INVERSE")
        self.assertEqual(inverse["prediction"], "Warriors")

    def test_create_inverse_prediction_prop_over(self):
        """Test creating inverse for over prop"""
        analysis = {
            "pk": "ANALYSIS#prop123",
            "sk": "value#LATEST",
            "prediction": "over 25.5",
            "confidence": 0.60,
            "analysis_type": "prop"
        }
        
        inverse = create_inverse_prediction(analysis)
        
        self.assertIsNotNone(inverse)
        self.assertIn("under", inverse["prediction"].lower())

    def test_create_inverse_prediction_prop_under(self):
        """Test creating inverse for under prop"""
        analysis = {
            "pk": "ANALYSIS#prop123",
            "sk": "value#LATEST",
            "prediction": "under 45.5",
            "confidence": 0.60,
            "analysis_type": "prop"
        }
        
        inverse = create_inverse_prediction(analysis)
        
        self.assertIsNotNone(inverse)
        self.assertIn("over", inverse["prediction"].lower())

    def test_create_inverse_prediction_unparseable(self):
        """Test inverse prediction with unparseable format"""
        analysis = {
            "pk": "ANALYSIS#game123",
            "sk": "consensus#LATEST",
            "prediction": "invalid format",
            "confidence": 0.65,
            "analysis_type": "game"
        }
        
        inverse = create_inverse_prediction(analysis)
        
        # Should return None for unparseable
        self.assertIsNone(inverse)


if __name__ == "__main__":
    unittest.main()
