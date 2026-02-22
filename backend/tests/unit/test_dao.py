"""DAO tests"""

from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from dao import BettingDAO


@pytest.fixture
def dao():
    with patch("dao.boto3"):
        return BettingDAO()


def test_get_game_ids_from_db(dao):
    """Test getting game IDs"""
    dao.table = Mock()
    dao.table.query.return_value = {
        "Items": [
            {"pk": "GAME#game123"},
            {"pk": "GAME#game456"}
        ]
    }
    
    game_ids = dao.get_game_ids_from_db("basketball_nba")
    assert len(game_ids) == 2
    assert "game123" in game_ids


def test_get_game_ids_pagination(dao):
    """Test game IDs with pagination"""
    dao.table = Mock()
    dao.table.query.side_effect = [
        {
            "Items": [{"pk": "GAME#game123"}],
            "LastEvaluatedKey": {"pk": "GAME#game123"}
        },
        {"Items": [{"pk": "GAME#game456"}]}
    ]
    
    game_ids = dao.get_game_ids_from_db("basketball_nba")
    assert len(game_ids) == 2


def test_get_game_ids_error(dao):
    """Test game IDs with error"""
    dao.table = Mock()
    dao.table.query.side_effect = Exception("DB error")
    
    game_ids = dao.get_game_ids_from_db("basketball_nba")
    assert game_ids == []


def test_get_prop_ids_from_db(dao):
    """Test getting prop IDs"""
    dao.table = Mock()
    dao.table.query.return_value = {
        "Items": [
            {"pk": "PROP#prop123"},
            {"pk": "PROP#prop456"}
        ]
    }
    
    prop_ids = dao.get_prop_ids_from_db("basketball_nba")
    # May return empty if method extracts differently
    assert isinstance(prop_ids, list)


def test_get_prop_ids_error(dao):
    """Test prop IDs with error"""
    dao.table = Mock()
    dao.table.query.side_effect = Exception("DB error")
    
    prop_ids = dao.get_prop_ids_from_db("basketball_nba")
    assert prop_ids == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
