"""Rest schedule model tests"""

from unittest.mock import Mock, patch

import pytest

from ml.models import RestScheduleModel


@pytest.fixture
def model():
    with patch("ml.models.boto3"):
        return RestScheduleModel()


def test_init(model):
    """Test init"""
    assert model.table is not None


def test_get_rest_score_no_data(model):
    """Test rest score with no data"""
    model.table.query = Mock(return_value={"Items": []})
    
    score = model._get_rest_score("basketball_nba", "lakers", "2024-01-15", True)
    assert score == 0.0


def test_get_rest_score_well_rested(model):
    """Test well rested team"""
    model.table.query = Mock(return_value={
        "Items": [{"rest_days": 3}]
    })
    
    score = model._get_rest_score("basketball_nba", "lakers", "2024-01-15", True)
    assert score > 0


def test_get_rest_score_back_to_back(model):
    """Test back-to-back game"""
    model.table.query = Mock(return_value={
        "Items": [{"rest_days": 0}]
    })
    
    score = model._get_rest_score("basketball_nba", "lakers", "2024-01-15", True)
    assert score < 0


def test_get_player_team_found(model):
    """Test finding player team"""
    model.table.query = Mock(return_value={
        "Items": [{"team": "Lakers"}]
    })
    
    team = model._get_player_team("basketball_nba", "lebron_james")
    assert team == "lakers"


def test_get_player_team_not_found(model):
    """Test player team not found"""
    model.table.query = Mock(return_value={"Items": []})
    
    team = model._get_player_team("basketball_nba", "unknown")
    assert team is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
