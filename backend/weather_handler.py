"""
Lambda handler for weather data collection
"""
import json
import os
from datetime import datetime, timedelta
import boto3
from weather_collector import WeatherCollector

def lambda_handler(event, context):
    """Collect weather data for upcoming games"""
    table = boto3.resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
    weather_collector = WeatherCollector()
    
    # Get upcoming games in next 48 hours
    now = datetime.utcnow()
    end_time = now + timedelta(hours=48)
    
    response = table.query(
        IndexName='ActiveBetsIndexV2',
        KeyConditionExpression='active_bet_pk = :pk AND commence_time BETWEEN :start AND :end',
        ExpressionAttributeValues={
            ':pk': f"GAME#{event.get('sport', 'basketball_nba')}",
            ':start': now.isoformat(),
            ':end': end_time.isoformat()
        }
    )
    
    games = response.get('Items', [])
    weather_collected = 0
    
    for game in games:
        try:
            game_id = game.get('pk', '').split('#')[1]
            venue = game.get('venue', '')
            # Extract city from venue or use home team location
            city = game.get('home_team', '').split()[-1]  # Simple city extraction
            sport = game.get('sport')
            game_time = game.get('commence_time')
            
            weather_data = weather_collector.get_weather_for_game(
                game_id, venue, city, sport, game_time
            )
            
            if weather_data:
                weather_collected += 1
                print(f"Collected weather for {game_id}: {weather_data.get('condition')}")
        except Exception as e:
            print(f"Error collecting weather for game {game.get('pk')}: {e}")
            continue
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'games_checked': len(games),
            'weather_collected': weather_collected
        })
    }
