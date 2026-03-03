"""Tests for NFL Efficiency Calculator"""

import pytest
from nfl_efficiency_calculator import NFLEfficiencyCalculator


def test_calculate_qb_efficiency():
    """Test QB passer rating calculation"""
    stats = {
        'completions': 20,
        'passingAttempts': 30,
        'passingYards': 250,
        'passingTouchdowns': 2,
        'interceptions': 1
    }
    
    rating = NFLEfficiencyCalculator.calculate_qb_efficiency(stats)
    assert rating > 0
    assert rating <= 158.3  # Max passer rating


def test_calculate_qb_efficiency_zero_attempts():
    """Test QB efficiency with zero attempts"""
    stats = {'passingAttempts': 0}
    
    rating = NFLEfficiencyCalculator.calculate_qb_efficiency(stats)
    assert rating == 0.0


def test_calculate_qb_efficiency_perfect():
    """Test perfect passer rating"""
    stats = {
        'completions': 10,
        'passingAttempts': 10,
        'passingYards': 125,  # 12.5 yards per attempt
        'passingTouchdowns': 2,
        'interceptions': 0
    }
    
    rating = NFLEfficiencyCalculator.calculate_qb_efficiency(stats)
    assert rating > 140  # Should be very high


def test_calculate_rb_efficiency():
    """Test RB efficiency calculation"""
    stats = {
        'rushingYards': 100,
        'rushingAttempts': 20,
        'receivingYards': 50,
        'receptions': 5,
        'rushingTouchdowns': 1,
        'receivingTouchdowns': 0
    }
    
    efficiency = NFLEfficiencyCalculator.calculate_rb_efficiency(stats)
    assert efficiency > 0
    # (100 + 50) / (20 + 5) + 1*2 = 6.0 + 2 = 8.0
    assert efficiency == 8.0


def test_calculate_rb_efficiency_zero_touches():
    """Test RB efficiency with zero touches"""
    stats = {
        'rushingAttempts': 0,
        'receptions': 0
    }
    
    efficiency = NFLEfficiencyCalculator.calculate_rb_efficiency(stats)
    assert efficiency == 0.0


def test_calculate_wr_efficiency():
    """Test WR efficiency calculation"""
    stats = {
        'receptions': 8,
        'receivingTargets': 10,
        'receivingYards': 120,
        'receivingTouchdowns': 1
    }
    
    efficiency = NFLEfficiencyCalculator.calculate_wr_efficiency(stats)
    assert efficiency > 0
    # (8/10)*10 + 120/10 + 1*2 = 8 + 12 + 2 = 22.0
    assert efficiency == 22.0


def test_calculate_wr_efficiency_zero_targets():
    """Test WR efficiency with zero targets"""
    stats = {'receivingTargets': 0}
    
    efficiency = NFLEfficiencyCalculator.calculate_wr_efficiency(stats)
    assert efficiency == 0.0


def test_calculate_player_efficiency_qb():
    """Test player efficiency auto-detects QB"""
    stats = {
        'passingAttempts': 30,
        'completions': 20,
        'passingYards': 250,
        'passingTouchdowns': 2,
        'interceptions': 1
    }
    
    efficiency = NFLEfficiencyCalculator.calculate_player_efficiency(stats)
    assert efficiency > 0


def test_calculate_player_efficiency_rb():
    """Test player efficiency auto-detects RB"""
    stats = {
        'rushingAttempts': 20,
        'rushingYards': 100,
        'receptions': 3,
        'receivingYards': 30,
        'rushingTouchdowns': 1,
        'receivingTouchdowns': 0
    }
    
    efficiency = NFLEfficiencyCalculator.calculate_player_efficiency(stats)
    assert efficiency > 0


def test_calculate_player_efficiency_wr():
    """Test player efficiency auto-detects WR"""
    stats = {
        'receptions': 8,
        'receivingTargets': 10,
        'receivingYards': 120,
        'receivingTouchdowns': 1,
        'rushingAttempts': 0
    }
    
    efficiency = NFLEfficiencyCalculator.calculate_player_efficiency(stats)
    assert efficiency > 0


def test_calculate_player_efficiency_explicit_position():
    """Test player efficiency with explicit position"""
    stats = {
        'receptions': 5,
        'receivingTargets': 8,
        'receivingYards': 60,
        'receivingTouchdowns': 0
    }
    
    efficiency = NFLEfficiencyCalculator.calculate_player_efficiency(stats, position='WR')
    assert efficiency > 0


def test_calculate_qb_efficiency_missing_stats():
    """Test QB efficiency handles missing stats gracefully"""
    stats = {}
    
    rating = NFLEfficiencyCalculator.calculate_qb_efficiency(stats)
    assert rating == 0.0


def test_calculate_rb_efficiency_missing_stats():
    """Test RB efficiency handles missing stats gracefully"""
    stats = {}
    
    efficiency = NFLEfficiencyCalculator.calculate_rb_efficiency(stats)
    assert efficiency == 0.0


def test_calculate_wr_efficiency_missing_stats():
    """Test WR efficiency handles missing stats gracefully"""
    stats = {}
    
    efficiency = NFLEfficiencyCalculator.calculate_wr_efficiency(stats)
    assert efficiency == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
