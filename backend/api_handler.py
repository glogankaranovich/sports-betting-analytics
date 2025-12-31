import json
import boto3
import os
from decimal import Decimal
from typing import Dict, Any, Optional

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
            'Access-Control-Allow-Headers': 'Content-Type'
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
        if sport:
            response = table.scan(
                FilterExpression=boto3.dynamodb.conditions.Attr('sport').eq(sport),
                Limit=limit
            )
        else:
            response = table.scan(Limit=limit)
        
        games = response.get('Items', [])
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
            KeyConditionExpression=boto3.dynamodb.conditions.Key('game_id').eq(game_id)
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
