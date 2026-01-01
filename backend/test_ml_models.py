"""
Test ML models functionality
"""

import pytest
import numpy as np
from ml.models import OddsAnalyzer, GamePrediction

def test_american_to_decimal():
    analyzer = OddsAnalyzer()
    
    # Positive odds
    assert analyzer.american_to_decimal(100) == 2.0
    assert analyzer.american_to_decimal(200) == 3.0
    
    # Negative odds
    assert analyzer.american_to_decimal(-100) == 2.0
    assert analyzer.american_to_decimal(-200) == 1.5

def test_decimal_to_probability():
    analyzer = OddsAnalyzer()
    
    assert analyzer.decimal_to_probability(2.0) == 0.5
    assert analyzer.decimal_to_probability(4.0) == 0.25

def test_analyze_game():
    analyzer = OddsAnalyzer()
    
    game_data = {
        'game_id': 'test_game',
        'sport': 'americanfootball_nfl',
        'home_team': 'Team A',
        'away_team': 'Team B',
        'odds': [
            {
                'bookmaker': 'betmgm',
                'markets': [{
                    'key': 'h2h',
                    'outcomes': [
                        {'price': -110},  # Home
                        {'price': -110}   # Away
                    ]
                }]
            },
            {
                'bookmaker': 'draftkings',
                'markets': [{
                    'key': 'h2h',
                    'outcomes': [
                        {'price': -105},  # Home
                        {'price': -115}   # Away
                    ]
                }]
            }
        ]
    }
    
    prediction = analyzer.analyze_game(game_data)
    
    assert isinstance(prediction, GamePrediction)
    assert 0 <= prediction.home_win_probability <= 1
    assert 0 <= prediction.away_win_probability <= 1
    assert 0 <= prediction.confidence_score <= 1
    assert isinstance(prediction.value_bets, list)
    
    # Probabilities should sum to ~1
    total_prob = prediction.home_win_probability + prediction.away_win_probability
    assert 0.95 <= total_prob <= 1.05

def test_empty_odds():
    analyzer = OddsAnalyzer()
    
    game_data = {
        'game_id': 'test_game',
        'odds': []
    }
    
    prediction = analyzer.analyze_game(game_data)
    
    assert prediction.home_win_probability == 0.5
    assert prediction.away_win_probability == 0.5
    assert prediction.confidence_score == 0.1
    assert prediction.value_bets == []
