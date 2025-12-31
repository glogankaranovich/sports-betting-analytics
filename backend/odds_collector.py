import os
import boto3
import requests
import json
from datetime import datetime
from typing import List, Dict, Any
from decimal import Decimal

def get_secret(secret_arn: str) -> str:
    """Retrieve secret from AWS Secrets Manager"""
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_arn)
    return response['SecretString']

def convert_floats_to_decimal(obj):
    """Convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(v) for v in obj]
    return obj

class OddsCollector:
    def __init__(self):
        secret_arn = os.getenv('ODDS_API_SECRET_ARN')
        if secret_arn:
            self.api_key = get_secret(secret_arn)
        else:
            self.api_key = os.getenv('ODDS_API_KEY')  # Fallback for local testing
        
        self.base_url = 'https://api.the-odds-api.com/v4'
        self.dynamodb = boto3.resource('dynamodb')
        self.table = self.dynamodb.Table(os.getenv('DYNAMODB_TABLE'))
    
    def get_active_sports(self) -> List[str]:
        """Get sports currently in season"""
        url = f"{self.base_url}/sports"
        params = {'api_key': self.api_key}
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        sports = response.json()
        # Filter for active sports (NFL, NBA for winter season)
        active = [sport['key'] for sport in sports if sport['active'] and sport['key'] in ['americanfootball_nfl', 'basketball_nba']]
        return active
    
    def get_odds(self, sport: str) -> List[Dict[str, Any]]:
        """Get odds for a specific sport"""
        url = f"{self.base_url}/sports/{sport}/odds"
        params = {
            'api_key': self.api_key,
            'regions': 'us',
            'markets': 'h2h,spreads,totals',
            'oddsFormat': 'american'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def store_odds(self, sport: str, odds_data: List[Dict[str, Any]]):
        """Store odds in DynamoDB with upsert logic"""
        for game in odds_data:
            game_id = game['id']
            
            for bookmaker in game['bookmakers']:
                # Use update_item for upsert behavior
                self.table.update_item(
                    Key={
                        'game_id': game_id,
                        'bookmaker': bookmaker['key']
                    },
                    UpdateExpression='SET sport = :sport, home_team = :home_team, away_team = :away_team, commence_time = :commence_time, markets = :markets, updated_at = :updated_at',
                    ExpressionAttributeValues={
                        ':sport': sport,
                        ':home_team': game['home_team'],
                        ':away_team': game['away_team'],
                        ':commence_time': game['commence_time'],
                        ':markets': convert_floats_to_decimal(bookmaker['markets']),
                        ':updated_at': datetime.utcnow().isoformat()
                    }
                )
    
    def collect_all_odds(self):
        """Main method to collect odds for all active sports"""
        active_sports = self.get_active_sports()
        print(f"Active sports: {active_sports}")
        
        total_games = 0
        for sport in active_sports:
            print(f"Collecting odds for {sport}...")
            odds = self.get_odds(sport)
            self.store_odds(sport, odds)
            total_games += len(odds)
            print(f"Stored {len(odds)} games for {sport}")
        
        return total_games

def lambda_handler(event, context):
    """AWS Lambda handler"""
    try:
        collector = OddsCollector()
        total_games = collector.collect_all_odds()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Successfully collected odds for {total_games} games',
                'timestamp': datetime.utcnow().isoformat()
            })
        }
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            })
        }

if __name__ == "__main__":
    # For local testing
    from dotenv import load_dotenv
    load_dotenv()
    collector = OddsCollector()
    collector.collect_all_odds()
