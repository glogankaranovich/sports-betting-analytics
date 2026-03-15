"""Tests for LearningEngine"""
import pytest
from unittest.mock import Mock
from benny.learning_engine import LearningEngine


@pytest.fixture
def mock_table():
    return Mock()


def test_get_adaptive_threshold_insufficient_data(mock_table):
    """Test threshold with no learned thresholds falls back to market-type defaults"""
    mock_table.get_item.return_value = {"Item": {"performance_by_sport": {}, "performance_by_market": {}}}
    engine = LearningEngine(mock_table)
    
    assert engine.get_adaptive_threshold("basketball_nba", "h2h") == 0.80
    assert engine.get_adaptive_threshold("basketball_nba", "spread") == 0.80
    assert engine.get_adaptive_threshold("basketball_nba", "player_points") == 0.65


def test_get_adaptive_threshold_poor_performance(mock_table):
    """Test game market threshold is 0.80 regardless of sport performance"""
    mock_table.get_item.return_value = {
        "Item": {
            "performance_by_sport": {"basketball_nba": {"wins": 12, "total": 30}},
            "performance_by_market": {}
        }
    }
    engine = LearningEngine(mock_table)
    
    assert engine.get_adaptive_threshold("basketball_nba", "h2h") == 0.80
    assert engine.get_adaptive_threshold("basketball_nba", "player_assists") == 0.65


def test_get_adaptive_threshold_good_performance(mock_table):
    """Test prop market threshold is 0.65 regardless of sport performance"""
    mock_table.get_item.return_value = {
        "Item": {
            "performance_by_sport": {"icehockey_nhl": {"wins": 20, "total": 30}},
            "performance_by_market": {}
        }
    }
    engine = LearningEngine(mock_table)
    
    assert engine.get_adaptive_threshold("icehockey_nhl", "h2h") == 0.80
    assert engine.get_adaptive_threshold("icehockey_nhl", "player_rebounds") == 0.65


def test_get_performance_warnings_with_data(mock_table):
    """Test performance warnings generation"""
    mock_table.get_item.return_value = {
        "Item": {
            "performance_by_sport": {
                "icehockey_nhl": {"wins": 20, "total": 30},
                "basketball_ncaab": {"wins": 5, "total": 30}
            },
            "performance_by_market": {}
        }
    }
    engine = LearningEngine(mock_table)
    
    warnings = engine.get_performance_warnings()
    
    assert "icehockey_nhl" in warnings.lower()
    assert "EXCEL" in warnings or "✅" in warnings


def test_get_performance_warnings_insufficient_data(mock_table):
    """Test warnings with insufficient data"""
    mock_table.get_item.return_value = {"Item": {"performance_by_sport": {}, "performance_by_market": {}}}
    engine = LearningEngine(mock_table)
    
    warnings = engine.get_performance_warnings()
    
    assert "Insufficient data" in warnings
