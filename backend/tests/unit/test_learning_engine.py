"""Tests for LearningEngine"""
import pytest
from unittest.mock import Mock
from benny.learning_engine import LearningEngine


@pytest.fixture
def mock_table():
    return Mock()


def test_get_adaptive_threshold_insufficient_data(mock_table):
    """Test threshold with insufficient data returns base"""
    mock_table.get_item.return_value = {"Item": {"performance_by_sport": {}, "performance_by_market": {}}}
    engine = LearningEngine(mock_table)
    
    threshold = engine.get_adaptive_threshold("basketball_nba", "h2h")
    
    assert threshold == 0.70


def test_get_adaptive_threshold_poor_performance(mock_table):
    """Test threshold increases for poor performance"""
    mock_table.get_item.return_value = {
        "Item": {
            "performance_by_sport": {"basketball_nba": {"wins": 12, "total": 30}},
            "performance_by_market": {}
        }
    }
    engine = LearningEngine(mock_table)
    
    threshold = engine.get_adaptive_threshold("basketball_nba", "h2h")
    
    assert threshold == 0.75


def test_get_adaptive_threshold_good_performance(mock_table):
    """Test threshold decreases for good performance"""
    mock_table.get_item.return_value = {
        "Item": {
            "performance_by_sport": {"icehockey_nhl": {"wins": 20, "total": 30}},
            "performance_by_market": {}
        }
    }
    engine = LearningEngine(mock_table)
    
    threshold = engine.get_adaptive_threshold("icehockey_nhl", "h2h")
    
    assert threshold == 0.65


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
