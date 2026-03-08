"""Tests for OpportunityAnalyzer"""
import pytest
from decimal import Decimal
from unittest.mock import Mock
from benny.opportunity_analyzer import OpportunityAnalyzer


@pytest.fixture
def mock_learning_engine():
    engine = Mock()
    engine.get_adaptive_threshold.return_value = 0.70
    return engine


def test_calculate_expected_value_positive_odds(mock_learning_engine):
    """Test EV calculation with positive odds"""
    analyzer = OpportunityAnalyzer(mock_learning_engine)
    
    ev = analyzer.calculate_expected_value(confidence=0.75, odds=200)
    
    assert ev > 0
    assert ev == (0.75 * 3.0) - 1


def test_calculate_expected_value_negative_odds(mock_learning_engine):
    """Test EV calculation with negative odds"""
    analyzer = OpportunityAnalyzer(mock_learning_engine)
    
    ev = analyzer.calculate_expected_value(confidence=0.75, odds=-150)
    
    assert ev > 0


def test_filter_opportunities_by_confidence(mock_learning_engine):
    """Test filtering by confidence threshold"""
    analyzer = OpportunityAnalyzer(mock_learning_engine)
    
    opportunities = [
        {"sport": "basketball_nba", "market_key": "h2h", "confidence": 0.80, "expected_value": 0.10},
        {"sport": "basketball_nba", "market_key": "h2h", "confidence": 0.60, "expected_value": 0.10},
    ]
    
    filtered = analyzer.filter_opportunities(opportunities, Decimal("100"))
    
    assert len(filtered) == 1
    assert filtered[0]["confidence"] == 0.80


def test_filter_opportunities_by_ev(mock_learning_engine):
    """Test filtering by minimum EV"""
    analyzer = OpportunityAnalyzer(mock_learning_engine)
    
    opportunities = [
        {"sport": "basketball_nba", "market_key": "h2h", "confidence": 0.80, "expected_value": 0.10},
        {"sport": "basketball_nba", "market_key": "h2h", "confidence": 0.80, "expected_value": 0.02},
    ]
    
    filtered = analyzer.filter_opportunities(opportunities, Decimal("100"))
    
    assert len(filtered) == 1
    assert filtered[0]["expected_value"] == 0.10


def test_rank_opportunities(mock_learning_engine):
    """Test ranking by EV"""
    analyzer = OpportunityAnalyzer(mock_learning_engine)
    
    opportunities = [
        {"expected_value": 0.05},
        {"expected_value": 0.15},
        {"expected_value": 0.10},
    ]
    
    ranked = analyzer.rank_opportunities(opportunities)
    
    assert ranked[0]["expected_value"] == 0.15
    assert ranked[1]["expected_value"] == 0.10
    assert ranked[2]["expected_value"] == 0.05
