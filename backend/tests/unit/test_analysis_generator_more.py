"""More analysis generator tests"""

import os
from unittest.mock import Mock, patch

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from analysis_generator import lambda_handler, decimal_to_float, float_to_decimal


def test_lambda_handler_games_only():
    """Test lambda handler for games only"""
    with patch("analysis_generator.ModelFactory") as mock_factory, \
         patch("analysis_generator.generate_game_analysis", return_value=5):
        
        mock_factory.create_model.return_value = Mock()
        
        event = {"sport": "basketball_nba", "model": "consensus", "bet_type": "games"}
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200


def test_lambda_handler_props_only():
    """Test lambda handler for props only"""
    with patch("analysis_generator.ModelFactory") as mock_factory, \
         patch("analysis_generator.generate_prop_analysis", return_value=3):
        
        mock_factory.create_model.return_value = Mock()
        
        event = {"sport": "basketball_nba", "model": "value", "bet_type": "props"}
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200


def test_lambda_handler_both():
    """Test lambda handler for both games and props"""
    with patch("analysis_generator.ModelFactory") as mock_factory, \
         patch("analysis_generator.generate_game_analysis", return_value=5), \
         patch("analysis_generator.generate_prop_analysis", return_value=3):
        
        mock_factory.create_model.return_value = Mock()
        
        event = {"sport": "basketball_nba", "model": "consensus", "bet_type": "both"}
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 200


def test_lambda_handler_error():
    """Test lambda handler error handling"""
    with patch("analysis_generator.ModelFactory.create_model", side_effect=Exception("Error")):
        
        event = {"sport": "basketball_nba"}
        response = lambda_handler(event, None)
        
        assert response["statusCode"] == 500


def test_decimal_to_float():
    """Test decimal to float conversion"""
    from decimal import Decimal
    
    obj = {"value": Decimal("1.5"), "nested": {"val": Decimal("2.5")}}
    result = decimal_to_float(obj)
    
    assert isinstance(result["value"], float)
    assert isinstance(result["nested"]["val"], float)


def test_float_to_decimal():
    """Test float to decimal conversion"""
    from decimal import Decimal
    
    obj = {"value": 1.5, "nested": {"val": 2.5}}
    result = float_to_decimal(obj)
    
    assert isinstance(result["value"], Decimal)
    assert isinstance(result["nested"]["val"], Decimal)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
