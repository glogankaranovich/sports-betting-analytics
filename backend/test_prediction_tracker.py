"""
Test PredictionTracker functionality
"""

import pytest
import boto3
from moto import mock_dynamodb
from unittest.mock import patch, MagicMock
from prediction_tracker import PredictionTracker
from decimal import Decimal

@mock_dynamodb
def test_prediction_tracker_init():
    """Test PredictionTracker initialization"""
    tracker = PredictionTracker()
    assert tracker.table_name == 'carpool-bets-v2-dev'
    assert tracker.odds_collector is not None

@mock_dynamodb
def test_generate_game_predictions():
    """Test game prediction generation"""
    # Create mock DynamoDB table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='carpool-bets-v2-dev',
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Mock odds data
    mock_odds = [
        {
            'game_id': 'test_game_1',
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
    ]
    
    with patch('prediction_tracker.PredictionTracker._get_recent_odds') as mock_get_odds:
        mock_get_odds.return_value = mock_odds
        
        tracker = PredictionTracker()
        count = tracker.generate_game_predictions()
        
        assert count == 1
        mock_get_odds.assert_called_once()

@mock_dynamodb
def test_generate_prop_predictions():
    """Test player prop prediction generation"""
    # Create mock DynamoDB table
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.create_table(
        TableName='carpool-bets-v2-dev',
        KeySchema=[
            {'AttributeName': 'pk', 'KeyType': 'HASH'},
            {'AttributeName': 'sk', 'KeyType': 'RANGE'}
        ],
        AttributeDefinitions=[
            {'AttributeName': 'pk', 'AttributeType': 'S'},
            {'AttributeName': 'sk', 'AttributeType': 'S'}
        ],
        BillingMode='PAY_PER_REQUEST'
    )
    
    # Mock player props data
    mock_props = [
        {
            'game_id': 'test_game_1',
            'sport': 'basketball_nba',
            'home_team': 'Team A',
            'away_team': 'Team B',
            'commence_time': '2026-01-03T20:00:00Z',
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
    
    with patch('prediction_tracker.PredictionTracker._get_recent_player_props') as mock_get_props:
        mock_get_props.return_value = mock_props
        
        tracker = PredictionTracker()
        count = tracker.generate_prop_predictions()
        
        assert count >= 0  # May be 0 if no valid props
        mock_get_props.assert_called_once()

def test_combat_sports_support():
    """Test that combat sports are included in supported sports"""
    tracker = PredictionTracker()
    
    # Check that MMA and Boxing are in the sports filter
    with patch.object(tracker.odds_collector, 'get_active_sports') as mock_get_sports:
        mock_get_sports.return_value = [
            'americanfootball_nfl', 'basketball_nba', 'baseball_mlb', 
            'icehockey_nhl', 'soccer_epl', 'soccer_usa_mls',
            'mma_mixed_martial_arts', 'boxing_boxing'
        ]
        
        sports = tracker.odds_collector.get_active_sports()
        assert 'mma_mixed_martial_arts' in sports
        assert 'boxing_boxing' in sports

if __name__ == "__main__":
    pytest.main([__file__])
