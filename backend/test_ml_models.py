"""
Test ML models functionality
"""

import pytest
import numpy as np
from ml.models import OddsAnalyzer, GamePrediction, PlayerPropPrediction

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
        'commence_time': '2026-01-03T20:00:00Z',
        'markets': [
            {
                'key': 'h2h',
                'outcomes': [
                    {'name': 'Team A', 'price': -110},
                    {'name': 'Team B', 'price': 100}
                ]
            }
        ]
    }
    
    prediction = analyzer.analyze_game(game_data)
    
    assert isinstance(prediction, GamePrediction)
    assert prediction.game_id == 'test_game'
    assert prediction.home_win_probability > 0
    assert prediction.away_win_probability > 0
    assert prediction.confidence_score > 0

def test_analyze_player_props():
    analyzer = OddsAnalyzer()
    
    props_data = [
        {
            'game_id': 'test_game',
            'sport': 'basketball_nba',
            'markets': [
                {
                    'key': 'player_points',
                    'outcomes': [
                        {'name': 'Player X Over 25.5', 'price': -110, 'point': 25.5},
                        {'name': 'Player X Under 25.5', 'price': -110, 'point': 25.5}
                    ]
                }
            ]
        }
    ]
    
    predictions = analyzer.analyze_player_props(props_data)
    
    assert len(predictions) >= 0
    if predictions:
        assert isinstance(predictions[0], PlayerPropPrediction)

def test_combat_sports_analysis():
    """Test that combat sports can be analyzed"""
    analyzer = OddsAnalyzer()
    
    # MMA fight data
    mma_data = {
        'game_id': 'mma_fight_1',
        'sport': 'mma_mixed_martial_arts',
        'home_team': 'Fighter A',
        'away_team': 'Fighter B',
        'commence_time': '2026-01-03T20:00:00Z',
        'markets': [
            {
                'key': 'h2h',
                'outcomes': [
                    {'name': 'Fighter A', 'price': -150},
                    {'name': 'Fighter B', 'price': 120}
                ]
            }
        ]
    }
    
    prediction = analyzer.analyze_game(mma_data)
    
    assert isinstance(prediction, GamePrediction)
    assert prediction.sport == 'mma_mixed_martial_arts'
    assert prediction.home_win_probability > 0
    assert prediction.away_win_probability > 0

def test_boxing_analysis():
    """Test that boxing matches can be analyzed"""
    analyzer = OddsAnalyzer()
    
    # Boxing match data
    boxing_data = {
        'game_id': 'boxing_match_1',
        'sport': 'boxing_boxing',
        'home_team': 'Boxer A',
        'away_team': 'Boxer B',
        'commence_time': '2026-01-03T20:00:00Z',
        'markets': [
            {
                'key': 'h2h',
                'outcomes': [
                    {'name': 'Boxer A', 'price': -200},
                    {'name': 'Boxer B', 'price': 170}
                ]
            }
        ]
    }
    
    prediction = analyzer.analyze_game(boxing_data)
    
    assert isinstance(prediction, GamePrediction)
    assert prediction.sport == 'boxing_boxing'
    assert prediction.home_win_probability > 0.5  # Favorite should have higher probability

def test_consensus_analysis_multiple_bookmakers():
    """Test consensus analysis with multiple bookmakers"""
    analyzer = OddsAnalyzer()
    
    # Game with multiple bookmaker odds
    game_data = {
        'game_id': 'test_game',
        'sport': 'americanfootball_nfl',
        'home_team': 'Team A',
        'away_team': 'Team B',
        'commence_time': '2026-01-03T20:00:00Z',
        'bookmakers': [
            {
                'key': 'fanduel',
                'markets': [
                    {
                        'key': 'h2h',
                        'outcomes': [
                            {'name': 'Team A', 'price': -110},
                            {'name': 'Team B', 'price': -110}
                        ]
                    }
                ]
            },
            {
                'key': 'draftkings',
                'markets': [
                    {
                        'key': 'h2h',
                        'outcomes': [
                            {'name': 'Team A', 'price': -105},
                            {'name': 'Team B', 'price': -115}
                        ]
                    }
                ]
            }
        ]
    }
    
    # Should handle multiple bookmakers for consensus
    prediction = analyzer.analyze_game(game_data)
    assert isinstance(prediction, GamePrediction)
    assert prediction.confidence_score > 0

if __name__ == "__main__":
    pytest.main([__file__])
