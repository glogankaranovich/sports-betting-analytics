"""Elo calculator tests"""

import os
from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from elo_calculator import EloCalculator


@pytest.fixture
def calculator():
    with patch("elo_calculator.boto3"):
        return EloCalculator()


def test_get_team_rating_new_team(calculator):
    """Test getting rating for new team"""
    calculator.table = Mock()
    calculator.table.query.return_value = {"Items": []}
    
    rating = calculator.get_team_rating("basketball_nba", "New Team")
    assert rating == 1500


def test_get_team_rating_existing_team(calculator):
    """Test getting rating for existing team"""
    calculator.table = Mock()
    calculator.table.query.return_value = {
        "Items": [{"rating": Decimal("1650")}]
    }
    
    rating = calculator.get_team_rating("basketball_nba", "Lakers")
    assert rating == 1650


def test_calculate_expected_score_equal(calculator):
    """Test expected score with equal ratings"""
    expected = calculator.calculate_expected_score(1500, 1500)
    assert expected == 0.5


def test_calculate_expected_score_favorite(calculator):
    """Test expected score for favorite"""
    expected = calculator.calculate_expected_score(1700, 1500)
    assert expected > 0.5


def test_update_ratings_home_win(calculator):
    """Test rating update for home win"""
    calculator.table = Mock()
    calculator.table.query.return_value = {"Items": []}
    
    new_home, new_away = calculator.update_ratings(
        "basketball_nba", "Lakers", "Warriors", 110, 105
    )
    
    # Home should gain rating
    assert new_home > 1500
    assert new_away < 1500


def test_update_ratings_tie(calculator):
    """Test rating update for tie"""
    calculator.table = Mock()
    calculator.table.query.return_value = {"Items": []}
    
    new_home, new_away = calculator.update_ratings(
        "soccer_epl", "Arsenal", "Chelsea", 2, 2
    )
    
    # Both should stay near 1500
    assert abs(new_home - 1500) < 20
    assert abs(new_away - 1500) < 20


def test_update_ratings_stores_results(calculator):
    """Test that update_ratings stores to DynamoDB"""
    calculator.table = Mock()
    calculator.table.query.return_value = {"Items": []}
    
    calculator.update_ratings("basketball_nba", "Lakers", "Warriors", 110, 105)
    
    # Should call put_item twice (once per team)
    assert calculator.table.put_item.call_count == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
