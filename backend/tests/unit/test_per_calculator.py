"""PER calculator tests"""

from unittest.mock import Mock, patch

import pytest


@patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"})
@patch("per_calculator.boto3")
def test_per_calculator_init(mock_boto):
    """Test PER calculator init"""
    from per_calculator import PERCalculator
    
    calc = PERCalculator()
    assert calc.table is not None


@patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"})
@patch("per_calculator.boto3")
def test_calculate_player_per_zero_minutes(mock_boto):
    """Test PER with zero minutes"""
    from per_calculator import PERCalculator
    
    calc = PERCalculator()
    per = calc.calculate_player_per({"minutes": 0})
    assert per == 0.0


@patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"})
@patch("per_calculator.boto3")
def test_calculate_player_per_with_stats(mock_boto):
    """Test PER calculation"""
    from per_calculator import PERCalculator
    
    calc = PERCalculator()
    stats = {
        "minutes": 30,
        "points": 25,
        "fieldGoalsMade": 10,
        "fieldGoalsAttempted": 20,
        "freeThrowsMade": 3,
        "freeThrowsAttempted": 4,
        "threePointFieldGoalsMade": 2,
        "assists": 5
    }
    per = calc.calculate_player_per(stats)
    assert per >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
