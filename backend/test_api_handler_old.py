"""
Comprehensive API Handler Tests
"""

import unittest
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
import os

# Import the module under test
import sys
sys.path.append('.')
from api_handler import (
    lambda_handler, 
    decimal_to_float, 
    create_response,
    handle_get_game_predictions, 
    handle_get_prop_predictions,
    handle_get_player_props,
    handle_get_games
)

class TestApiHandler(unittest.TestCase):
    
    def setUp(self):
        """Set up test environment"""
        os.environ['DYNAMODB_TABLE'] = 'test-table'
        os.environ['ENVIRONMENT'] = 'test'
    
    def test_decimal_to_float_conversion(self):
        """Test decimal to float conversion utility"""
        # Test with nested dictionary containing Decimals
        data = {
            'price': Decimal('100.50'),
            'nested': {
                'value': Decimal('25.75'),
                'string': 'test'
            },
            'list': [Decimal('1.5'), 'text', Decimal('2.5')]
        }
        
        result = decimal_to_float(data)
        
        self.assertEqual(result['price'], 100.5)
        self.assertEqual(result['nested']['value'], 25.75)
        self.assertEqual(result['nested']['string'], 'test')
        self.assertEqual(result['list'][0], 1.5)
        self.assertEqual(result['list'][1], 'text')
        self.assertEqual(result['list'][2], 2.5)

    @patch('api_handler.boto3.resource')
    def test_health_endpoint(self, mock_resource):
        """Test health check endpoint"""
        mock_table = Mock()
        mock_resource.return_value.Table.return_value = mock_table
        
        event = {
            'httpMethod': 'GET',
            'path': '/health',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        body = json.loads(response['body'])
        self.assertEqual(body['status'], 'healthy')

    def test_unknown_endpoint(self):
        """Test unknown endpoint returns 404"""
        event = {
            'httpMethod': 'GET',
            'path': '/unknown',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        self.assertEqual(response['statusCode'], 404)

    def test_handle_get_game_predictions(self):
        """Test game predictions API endpoint"""
        query_params = {'limit': '10'}
        
        mock_predictions = [
            {
                'pk': 'GAME_PRED#test_game_1',
                'sk': '2026-01-03T20:00:00Z',
                'game_id': 'test_game_1',
                'sport': 'americanfootball_nfl',
                'home_team': 'Team A',
                'away_team': 'Team B',
                'prediction': {
                    'home_win_probability': 0.55,
                    'away_win_probability': 0.45,
                    'confidence_score': 0.75
                }
            }
        ]
        
        with patch('api_handler.get_game_predictions') as mock_get:
            mock_get.return_value = mock_predictions
            
            response = handle_get_game_predictions(query_params)
            
            self.assertEqual(response['statusCode'], 200)
            body = json.loads(response['body'])
            self.assertEqual(len(body['predictions']), 1)
            self.assertEqual(body['predictions'][0]['sport'], 'americanfootball_nfl')
            mock_get.assert_called_once_with(10)

    def test_handle_get_prop_predictions(self):
        """Test prop predictions API endpoint"""
        query_params = {'limit': '5'}
        
        mock_predictions = [
            {
                'pk': 'PROP_PRED#test_game_1#player_points',
                'sk': '2026-01-03T20:00:00Z',
                'game_id': 'test_game_1',
                'sport': 'basketball_nba',
                'market': 'player_points',
                'player_name': 'Player X',
                'prediction': {
                    'over_probability': 0.60,
                    'under_probability': 0.40,
                    'confidence_score': 0.80
                }
            }
        ]
        
        with patch('api_handler.get_prop_predictions') as mock_get:
            mock_get.return_value = mock_predictions
            
            response = handle_get_prop_predictions(query_params)
            
            self.assertEqual(response['statusCode'], 200)
            body = json.loads(response['body'])
            self.assertEqual(len(body['predictions']), 1)
            self.assertEqual(body['predictions'][0]['market'], 'player_points')
            mock_get.assert_called_once_with(5)

    def test_handle_get_player_props(self):
        """Test player props API endpoint"""
        query_params = {}
        
        mock_props = [
            {
                'game_id': 'test_game_1',
                'sport': 'basketball_nba',
                'home_team': 'Team A',
                'away_team': 'Team B',
                'bookmaker': 'fanduel',
                'markets': [
                    {
                        'key': 'player_points',
                        'outcomes': [
                            {'name': 'Player X Over 25.5', 'price': -110}
                        ]
                    }
                ]
            }
        ]
        
        with patch('api_handler.get_player_props') as mock_get:
            mock_get.return_value = mock_props
            
            response = handle_get_player_props(query_params)
            
            self.assertEqual(response['statusCode'], 200)
            body = json.loads(response['body'])
            self.assertEqual(len(body['player_props']), 1)
            self.assertEqual(body['player_props'][0]['sport'], 'basketball_nba')

    def test_bookmaker_filtering(self):
        """Test that API responses filter to display bookmakers"""
        query_params = {}
        
        # Mock data with multiple bookmakers
        mock_games = [
            {
                'game_id': 'test_game_1',
                'bookmaker': 'fanduel',  # Should be included
                'sport': 'americanfootball_nfl'
            },
            {
                'game_id': 'test_game_1', 
                'bookmaker': 'pinnacle',  # Should be filtered out
                'sport': 'americanfootball_nfl'
            },
            {
                'game_id': 'test_game_1',
                'bookmaker': 'draftkings',  # Should be included
                'sport': 'americanfootball_nfl'
            }
        ]
        
        with patch('api_handler.get_games') as mock_get:
            mock_get.return_value = mock_games
            
            response = handle_get_games(query_params)
            
            body = json.loads(response['body'])
            bookmakers = [game['bookmaker'] for game in body['games']]
            
            self.assertIn('fanduel', bookmakers)
            self.assertIn('draftkings', bookmakers)
            self.assertNotIn('pinnacle', bookmakers)

    def test_combat_sports_api_support(self):
        """Test that API endpoints handle combat sports"""
        query_params = {}
        
        mock_games = [
            {
                'game_id': 'mma_fight_1',
                'sport': 'mma_mixed_martial_arts',
                'home_team': 'Fighter A',
                'away_team': 'Fighter B',
                'bookmaker': 'fanduel'
            },
            {
                'game_id': 'boxing_match_1',
                'sport': 'boxing_boxing', 
                'home_team': 'Boxer A',
                'away_team': 'Boxer B',
                'bookmaker': 'draftkings'
            }
        ]
        
        with patch('api_handler.get_games') as mock_get:
            mock_get.return_value = mock_games
            
            response = handle_get_games(query_params)
            
            body = json.loads(response['body'])
            sports = [game['sport'] for game in body['games']]
            
            self.assertIn('mma_mixed_martial_arts', sports)
            self.assertIn('boxing_boxing', sports)

if __name__ == "__main__":
    unittest.main()
        test_data = {
            'price': Decimal('1.5'),
            'nested': {
                'value': Decimal('2.75'),
                'list': [Decimal('3.25'), 'string', 42]
            }
        }
        
        result = decimal_to_float(test_data)
        
        self.assertEqual(result['price'], 1.5)
        self.assertEqual(result['nested']['value'], 2.75)
        self.assertEqual(result['nested']['list'][0], 3.25)
        self.assertEqual(result['nested']['list'][1], 'string')
        self.assertEqual(result['nested']['list'][2], 42)
    
    def test_create_response(self):
        """Test API response creation with CORS headers"""
        body = {'message': 'test'}
        response = create_response(200, body)
        
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
        self.assertEqual(response['headers']['Access-Control-Allow-Origin'], '*')
        self.assertEqual(json.loads(response['body']), body)
    
    @patch('api_handler.table')
    def test_health_endpoint(self, mock_table):
        """Test health check endpoint"""
        event = {
            'httpMethod': 'GET',
            'path': '/health',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(body['status'], 'healthy')
        self.assertEqual(body['table'], 'test-table')
        self.assertEqual(body['environment'], 'test')
    
    def test_cors_preflight(self):
        """Test CORS preflight OPTIONS request"""
        event = {
            'httpMethod': 'OPTIONS',
            'path': '/games',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('Access-Control-Allow-Origin', response['headers'])
    
    @patch('api_handler.table')
    def test_get_games_all(self, mock_table):
        """Test getting all games"""
        # Mock DynamoDB response
        mock_table.scan.return_value = {
            'Items': [
                {
                    'pk': 'GAME#game1',
                    'sk': 'betmgm#h2h',
                    'sport': 'americanfootball_nfl',
                    'home_team': 'Team A',
                    'away_team': 'Team B',
                    'bookmaker': 'betmgm',
                    'market_key': 'h2h',
                    'outcomes': [{'name': 'Team A', 'price': -150}],
                    'updated_at': '2026-01-01T12:00:00'
                }
            ]
        }
        
        event = {
            'httpMethod': 'GET',
            'path': '/games',
            'queryStringParameters': {'limit': '50'}
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(len(body['games']), 1)
        self.assertEqual(body['games'][0]['game_id'], 'game1')
        self.assertEqual(body['games'][0]['odds'], 1.5)  # Decimal converted to float
        mock_table.scan.assert_called_once()
    
    @patch('api_handler.table')
    def test_get_games_filtered_by_sport(self, mock_table):
        """Test getting games filtered by sport"""
        mock_table.scan.return_value = {'Items': []}
        
        event = {
            'httpMethod': 'GET',
            'path': '/games',
            'queryStringParameters': {'sport': 'americanfootball_nfl', 'limit': '100'}
        }
        
        response = lambda_handler(event, {})
        
        self.assertEqual(response['statusCode'], 200)
        mock_table.scan.assert_called_once()
        # Verify filter was applied
        call_args = mock_table.scan.call_args
        self.assertIn('FilterExpression', call_args[1])
    
    @patch('api_handler.table')
    def test_get_game_by_id_found(self, mock_table):
        """Test getting a specific game by ID"""
        mock_table.query.return_value = {
            'Items': [
                {
                    'game_id': 'game123',
                    'bookmaker': 'betmgm',
                    'odds': Decimal('2.0')
                },
                {
                    'game_id': 'game123',
                    'bookmaker': 'draftkings',
                    'odds': Decimal('1.8')
                }
            ]
        }
        
        event = {
            'httpMethod': 'GET',
            'path': '/games/game123',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(body['game_id'], 'game123')
        self.assertEqual(len(body['bookmakers']), 2)
        self.assertEqual(body['count'], 2)
    
    @patch('api_handler.table')
    def test_get_game_by_id_not_found(self, mock_table):
        """Test getting a non-existent game"""
        mock_table.query.return_value = {'Items': []}
        
        event = {
            'httpMethod': 'GET',
            'path': '/games/nonexistent',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        self.assertEqual(response['statusCode'], 404)
        self.assertEqual(body['error'], 'Game not found')
    
    @patch('api_handler.table')
    def test_get_sports(self, mock_table):
        """Test getting list of sports"""
        mock_table.scan.return_value = {
            'Items': [
                {'sport': 'americanfootball_nfl'},
                {'sport': 'basketball_nba'},
                {'sport': 'americanfootball_nfl'},  # Duplicate should be deduplicated
            ]
        }
        
        event = {
            'httpMethod': 'GET',
            'path': '/sports',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(len(body['sports']), 2)
        self.assertIn('americanfootball_nfl', body['sports'])
        self.assertIn('basketball_nba', body['sports'])
    
    @patch('api_handler.table')
    def test_get_bookmakers(self, mock_table):
        """Test getting list of bookmakers"""
        mock_table.scan.return_value = {
            'Items': [
                {'bookmaker': 'betmgm'},
                {'bookmaker': 'draftkings'},
                {'bookmaker': 'betmgm'},  # Duplicate should be deduplicated
            ]
        }
        
        event = {
            'httpMethod': 'GET',
            'path': '/bookmakers',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        self.assertEqual(response['statusCode'], 200)
        self.assertEqual(len(body['bookmakers']), 2)
        self.assertIn('betmgm', body['bookmakers'])
        self.assertIn('draftkings', body['bookmakers'])
    
    def test_unknown_endpoint(self):
        """Test unknown endpoint returns 404"""
        event = {
            'httpMethod': 'GET',
            'path': '/unknown',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        self.assertEqual(response['statusCode'], 404)
        self.assertEqual(body['error'], 'Endpoint not found')
    
    @patch('api_handler.table')
    def test_database_error_handling(self, mock_table):
        """Test error handling when database fails"""
        mock_table.scan.side_effect = Exception('Database connection failed')
        
        event = {
            'httpMethod': 'GET',
            'path': '/games',
            'queryStringParameters': None
        }
        
        response = lambda_handler(event, {})
        body = json.loads(response['body'])
        
        self.assertEqual(response['statusCode'], 500)
        self.assertIn('Error fetching games', body['error'])

if __name__ == '__main__':
    unittest.main()
