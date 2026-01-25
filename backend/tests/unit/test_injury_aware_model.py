"""Unit tests for Injury-Aware Model"""

import pytest
from unittest.mock import Mock, patch
from ml.models import InjuryAwareModel


@pytest.fixture
def mock_table():
    return Mock()


@pytest.fixture
def model(mock_table):
    return InjuryAwareModel(dynamodb_table=mock_table)


@pytest.fixture
def game_info():
    return {
        "home_team": "Atlanta Hawks",
        "away_team": "Boston Celtics",
        "sport": "basketball_nba",
        "commence_time": "2026-01-25T19:00:00Z",
    }


@pytest.fixture
def odds_items():
    return [
        {
            "sk": "ODDS#spreads#fanduel",
            "outcomes": [
                {"name": "Atlanta Hawks", "point": -3.5},
                {"name": "Boston Celtics", "point": 3.5},
            ],
        }
    ]


def test_analyze_game_with_away_injuries(model, mock_table, game_info, odds_items):
    """Test game analysis when away team has more injuries"""
    mock_table.query.side_effect = [
        {"Items": [{"injuries": []}]},  # Home team healthy
        {
            "Items": [{"injuries": [{"status": "Out"}, {"status": "Out"}]}]
        },  # Away team injured
    ]

    result = model.analyze_game_odds("game123", odds_items, game_info)

    assert result.model == "injury_aware"
    assert result.confidence >= 0.65
    assert "Atlanta Hawks" in result.prediction
    assert "injuries" in result.reasoning.lower()


def test_analyze_game_with_home_injuries(model, mock_table, game_info, odds_items):
    """Test game analysis when home team has more injuries"""
    mock_table.query.side_effect = [
        {
            "Items": [{"injuries": [{"status": "Out"}, {"status": "Out"}]}]
        },  # Home injured
        {"Items": [{"injuries": []}]},  # Away healthy
    ]

    result = model.analyze_game_odds("game123", odds_items, game_info)

    assert result.model == "injury_aware"
    assert result.confidence >= 0.65
    assert "Boston Celtics" in result.prediction


def test_analyze_game_both_healthy(model, mock_table, game_info, odds_items):
    """Test game analysis when both teams are healthy"""
    mock_table.query.side_effect = [
        {"Items": [{"injuries": []}]},
        {"Items": [{"injuries": []}]},
    ]

    result = model.analyze_game_odds("game123", odds_items, game_info)

    assert result.model == "injury_aware"
    assert result.confidence == 0.55
    assert "healthy" in result.reasoning.lower()


def test_analyze_prop_player_out(model):
    """Test prop analysis when player is out"""
    prop_item = {
        "event_id": "game123",
        "player_name": "Trae Young",
        "sport": "basketball_nba",
        "market_key": "player_points",
        "point": 25.5,
        "home_team": "Atlanta Hawks",
        "away_team": "Boston Celtics",
        "commence_time": "2026-01-25T19:00:00Z",
    }

    with patch.object(model, "_get_player_injury_status") as mock_injury:
        mock_injury.return_value = {"status": "Out", "injury_type": "Knee"}

        result = model.analyze_prop_odds(prop_item)

        assert result.prediction == "AVOID"
        assert result.confidence == 0.9
        assert "Out" in result.reasoning


def test_analyze_prop_player_healthy(model):
    """Test prop analysis when player is healthy"""
    prop_item = {
        "event_id": "game123",
        "player_name": "Trae Young",
        "sport": "basketball_nba",
        "market_key": "player_points",
        "point": 25.5,
        "home_team": "Atlanta Hawks",
        "away_team": "Boston Celtics",
        "commence_time": "2026-01-25T19:00:00Z",
    }

    with patch.object(model, "_get_player_injury_status") as mock_injury:
        mock_injury.return_value = None

        result = model.analyze_prop_odds(prop_item)

        assert "Over" in result.prediction
        assert result.confidence == 0.55
        assert "healthy" in result.reasoning.lower()


def test_calculate_injury_impact_no_injuries(model):
    """Test injury impact calculation with no injuries"""
    impact = model._calculate_injury_impact([])
    assert impact == 0.0


def test_calculate_injury_impact_multiple_injuries(model):
    """Test injury impact calculation with multiple injuries"""
    injuries = [{"status": "Out"}, {"status": "Out"}, {"status": "Out"}]
    impact = model._calculate_injury_impact(injuries)
    assert abs(impact - 0.45) < 0.01  # 3 * 0.15


def test_calculate_injury_impact_max_cap(model):
    """Test injury impact is capped at 1.0"""
    injuries = [{"status": "Out"}] * 10
    impact = model._calculate_injury_impact(injuries)
    assert impact == 1.0


def test_get_team_injuries_no_data(model, mock_table):
    """Test getting team injuries when no data exists"""
    mock_table.query.return_value = {"Items": []}

    injuries = model._get_team_injuries("Atlanta Hawks", "basketball_nba")

    assert injuries == []


def test_get_team_injuries_with_data(model, mock_table):
    """Test getting team injuries with data"""
    mock_table.query.return_value = {
        "Items": [
            {
                "injuries": [
                    {"status": "Out", "player": "Player 1"},
                    {"status": "Questionable", "player": "Player 2"},
                    {"status": "Out", "player": "Player 3"},
                ]
            }
        ]
    }

    injuries = model._get_team_injuries("Atlanta Hawks", "basketball_nba")

    assert len(injuries) == 2  # Only "Out" status
    assert all(inj["status"] == "Out" for inj in injuries)
