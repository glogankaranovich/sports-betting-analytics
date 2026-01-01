import json
import boto3
import os
from decimal import Decimal
from typing import Dict, Any, Optional
from ml.models import OddsAnalyzer

# DynamoDB setup
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table_name = os.getenv('DYNAMODB_TABLE')
table = dynamodb.Table(table_name)

def decimal_to_float(obj):
    """Convert Decimal objects to float for JSON serialization"""
    if isinstance(obj, Decimal):
        return float(obj)
    elif isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decimal_to_float(v) for v in obj]
    return obj

def create_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Create API Gateway response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
            'Access-Control-Allow-Headers': 'Content-Type, Authorization'
        },
        'body': json.dumps(body, default=str)
    }

def lambda_handler(event, context):
    """Main Lambda handler for API requests"""
    try:
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        query_params = event.get('queryStringParameters') or {}
        
        # Handle CORS preflight
        if http_method == 'OPTIONS':
            return create_response(200, {'message': 'CORS preflight'})
        
        # Route requests
        if path == '/health':
            return handle_health()
        elif path == '/games':
            return handle_get_games(query_params)
        elif path.startswith('/games/'):
            game_id = path.split('/')[-1]
            return handle_get_game(game_id)
        elif path == '/predictions':
            return handle_get_predictions(query_params)
        elif path == '/stored-predictions':
            return handle_get_stored_predictions(query_params)
        elif path == '/sports':
            return handle_get_sports()
        elif path == '/bookmakers':
            return handle_get_bookmakers()
        else:
            return create_response(404, {'error': 'Endpoint not found'})
            
    except Exception as e:
        return create_response(500, {'error': f'Internal server error: {str(e)}'})

def handle_health():
    """Health check endpoint"""
    return create_response(200, {
        'status': 'healthy',
        'table': table_name,
        'environment': os.getenv('ENVIRONMENT', 'unknown')
    })

def handle_get_games(query_params: Dict[str, str]):
    """Get all games, optionally filtered by sport"""
    sport = query_params.get('sport')
    limit = int(query_params.get('limit', '100'))
    
    try:
        # Filter out prediction records (pk doesn't start with PRED#)
        base_filter = boto3.dynamodb.conditions.Attr('pk').not_exists() | ~boto3.dynamodb.conditions.Attr('pk').begins_with('PRED#')
        
        if sport:
            filter_expression = base_filter & boto3.dynamodb.conditions.Attr('sport').eq(sport)
        else:
            filter_expression = base_filter
        
        games = []
        last_evaluated_key = None
        
        while True:
            scan_kwargs = {
                'FilterExpression': filter_expression,
                'Limit': limit
            }
            if last_evaluated_key:
                scan_kwargs['ExclusiveStartKey'] = last_evaluated_key
                
            response = table.scan(**scan_kwargs)
            games.extend(response.get('Items', []))
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        games = decimal_to_float(games)
        
        return create_response(200, {
            'games': games,
            'count': len(games),
            'sport_filter': sport
        })
    except Exception as e:
        return create_response(500, {'error': f'Error fetching games: {str(e)}'})

def handle_get_game(game_id: str):
    """Get all betting data for a specific game"""
    try:
        response = table.query(
            KeyConditionExpression=boto3.dynamodb.conditions.Key('pk').eq(game_id)
        )
        
        game_data = response.get('Items', [])
        
        if not game_data:
            return create_response(404, {'error': 'Game not found'})
        
        game_data = decimal_to_float(game_data)
        
        return create_response(200, {
            'game_id': game_id,
            'bookmakers': game_data,
            'count': len(game_data)
        })
    except Exception as e:
        return create_response(500, {'error': f'Error fetching game: {str(e)}'})

def handle_get_sports():
    """Get list of available sports"""
    try:
        response = table.scan(ProjectionExpression="sport")
        
        sports = set()
        for item in response.get('Items', []):
            if 'sport' in item:
                sports.add(item['sport'])
        
        return create_response(200, {
            'sports': sorted(list(sports)),
            'count': len(sports)
        })
    except Exception as e:
        return create_response(500, {'error': f'Error fetching sports: {str(e)}'})

def handle_get_bookmakers():
    """Get list of available bookmakers"""
    try:
        response = table.scan(ProjectionExpression="bookmaker")
        
        bookmakers = set()
        for item in response.get('Items', []):
            if 'bookmaker' in item:
                bookmakers.add(item['bookmaker'])
        
        return create_response(200, {
            'bookmakers': sorted(list(bookmakers)),
            'count': len(bookmakers)
        })
    except Exception as e:
        return create_response(500, {'error': f'Error fetching bookmakers: {str(e)}'})

def handle_get_predictions(query_params: Dict[str, str]):
    """Get ML predictions for games"""
    sport = query_params.get('sport')
    limit = int(query_params.get('limit', '50'))
    
    try:
        # Get games data
        if sport:
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('sport').eq(sport),
                Limit=limit
            )
        else:
            response = table.scan(Limit=limit)
        
        # Group by game_id and generate predictions
        games_by_id = {}
        for item in response.get('Items', []):
            game_id = item.get('pk')  # Use pk instead of game_id
            if game_id not in games_by_id:
                games_by_id[game_id] = {
                    'game_id': game_id,
                    'sport': item.get('sport'),
                    'home_team': item.get('home_team'),
                    'away_team': item.get('away_team'),
                    'commence_time': item.get('commence_time'),
                    'odds': []
                }
            
            games_by_id[game_id]['odds'].append({
                'bookmaker': item.get('sk'),  # Use sk instead of bookmaker
                'markets': item.get('markets', [])
            })
        
        # Generate predictions
        analyzer = OddsAnalyzer()
        predictions = []
        
        for game_data in games_by_id.values():
            try:
                prediction = analyzer.analyze_game(game_data)
                predictions.append({
                    'game_id': game_data['game_id'],
                    'sport': game_data['sport'],
                    'home_team': game_data['home_team'],
                    'away_team': game_data['away_team'],
                    'commence_time': game_data['commence_time'],
                    'home_win_probability': prediction.home_win_probability,
                    'away_win_probability': prediction.away_win_probability,
                    'confidence_score': prediction.confidence_score,
                    'value_bets': prediction.value_bets
                })
            except Exception as e:
                # Skip games with prediction errors
                continue
        
        return create_response(200, {
            'predictions': predictions,
            'count': len(predictions)
        })
    except Exception as e:
        return create_response(500, {'error': f'Error generating predictions: {str(e)}'})

def handle_get_stored_predictions(query_params: Dict[str, str]):
    """Get stored predictions from database"""
    limit = int(query_params.get('limit', '50'))
    
    try:
        from prediction_tracker import PredictionTracker
        tracker = PredictionTracker(table_name)
        predictions = tracker.get_predictions(limit)
        
        return create_response(200, {
            'predictions': predictions,
            'count': len(predictions)
        })
    except Exception as e:
        return create_response(500, {'error': f'Error fetching stored predictions: {str(e)}'})
