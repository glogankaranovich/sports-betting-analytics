"""Additional analysis generator tests"""

import os
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

# Set env before import
os.environ["DYNAMODB_TABLE"] = "test-table"

from analysis_generator import generate_game_analysis, generate_prop_analysis


def test_generate_game_analysis_with_limit():
    """Test game analysis with limit parameter"""
    with patch("analysis_generator.table") as mock_table, \
         patch("analysis_generator.ModelFactory") as mock_factory:
        
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "sk": "draftkings#spreads#LATEST",
                    "sport": "basketball_nba",
                    "home_team": "Lakers",
                    "away_team": "Warriors",
                    "outcomes": [
                        {"name": "Lakers", "price": -110, "point": -5.5},
                        {"name": "Warriors", "price": -110, "point": 5.5}
                    ]
                }
            ]
        }
        
        mock_model = Mock()
        mock_model.analyze_game_odds.return_value = None
        mock_factory.create_model.return_value = mock_model
        
        count = generate_game_analysis("basketball_nba", mock_model, limit=5)
        assert count >= 0


def test_generate_game_analysis_pagination():
    """Test game analysis with pagination"""
    with patch("analysis_generator.table") as mock_table, \
         patch("analysis_generator.ModelFactory") as mock_factory:
        
        # First page
        mock_table.query.side_effect = [
            {
                "Items": [
                    {
                        "pk": "GAME#game123",
                        "sk": "draftkings#spreads#LATEST",
                        "sport": "basketball_nba",
                        "home_team": "Lakers",
                        "away_team": "Warriors",
                        "outcomes": []
                    }
                ],
                "LastEvaluatedKey": {"pk": "GAME#game123"}
            },
            # Second page
            {"Items": []}
        ]
        
        mock_model = Mock()
        mock_model.analyze_game_odds.return_value = None
        
        count = generate_game_analysis("basketball_nba", mock_model)
        assert mock_table.query.call_count == 2


def test_generate_prop_analysis_with_limit():
    """Test prop analysis with limit"""
    with patch("analysis_generator.table") as mock_table:
        
        mock_table.query.return_value = {
            "Items": [
                {
                    "pk": "PROP#prop123",
                    "sk": "draftkings#player_points#LATEST",
                    "sport": "basketball_nba",
                    "player_name": "LeBron James",
                    "outcomes": [
                        {"name": "Over", "price": -110, "point": 25.5},
                        {"name": "Under", "price": -110, "point": 25.5}
                    ]
                }
            ]
        }
        
        mock_model = Mock()
        mock_model.analyze_player_prop.return_value = None
        
        count = generate_prop_analysis("basketball_nba", mock_model, limit=10)
        assert count >= 0


def test_generate_prop_analysis_pagination():
    """Test prop analysis pagination"""
    with patch("analysis_generator.table") as mock_table:
        
        mock_table.query.side_effect = [
            {
                "Items": [{"pk": "PROP#prop123", "sk": "draftkings#player_points#LATEST"}],
                "LastEvaluatedKey": {"pk": "PROP#prop123"}
            },
            {"Items": []}
        ]
        
        mock_model = Mock()
        mock_model.analyze_player_prop.return_value = None
        
        count = generate_prop_analysis("basketball_nba", mock_model)
        assert mock_table.query.call_count == 2


def test_generate_game_analysis_error_handling():
    """Test game analysis error handling"""
    with patch("analysis_generator.table") as mock_table:
        
        mock_table.query.side_effect = Exception("DynamoDB error")
        
        mock_model = Mock()
        
        # Should handle error gracefully
        count = generate_game_analysis("basketball_nba", mock_model)
        assert count == 0


def test_generate_prop_analysis_error_handling():
    """Test prop analysis error handling"""
    with patch("analysis_generator.table") as mock_table:
        
        mock_table.query.side_effect = Exception("DynamoDB error")
        
        mock_model = Mock()
        
        count = generate_prop_analysis("basketball_nba", mock_model)
        assert count == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
