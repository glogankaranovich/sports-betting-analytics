import os
import boto3
import requests
import json
from datetime import datetime, timedelta
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
    
    def get_player_props(self, sport: str, event_id: str) -> List[Dict[str, Any]]:
        """Get player props for a specific event"""
        url = f"{self.base_url}/sports/{sport}/events/{event_id}/odds"
        params = {
            'api_key': self.api_key,
            'regions': 'us',
            'markets': 'player_pass_tds,player_pass_yds,player_rush_yds,player_receptions,player_reception_yds,player_points,player_rebounds,player_assists',
            'oddsFormat': 'american'
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        return response.json()
    
    def store_player_props(self, sport: str, event_id: str, props_data: Dict[str, Any]):
        """Store player props in DynamoDB"""
        # Collect from ALL bookmakers for better prediction accuracy
        # Frontend will filter to display only specific bookmakers
        
        for bookmaker in props_data.get('bookmakers', []):
                
            for market in bookmaker.get('markets', []):
                for outcome in market.get('outcomes', []):
                    # Extract player name from outcome description
                    player_name = outcome.get('description', 'Unknown')
                    
                    # Create timestamped sort key for historical tracking
                    timestamp = datetime.utcnow().isoformat()
                    pk = f"PROP#{event_id}#{player_name}"
                    sk_historical = f"{bookmaker['key']}#{market['key']}#{outcome['name']}#{timestamp}"
                    sk_latest = f"{bookmaker['key']}#{market['key']}#{outcome['name']}#LATEST"
                    
                    # Calculate TTL (2 days after game commence time)
                    commence_dt = datetime.fromisoformat(props_data['commence_time'].replace('Z', '+00:00'))
                    ttl = int((commence_dt + timedelta(days=2)).timestamp())
                    
                    item_data = {
                        'pk': pk,
                        'sport': sport,
                        'event_id': event_id,
                        'bookmaker': bookmaker['key'],
                        'market_key': market['key'],
                        'player_name': player_name,
                        'outcome': outcome['name'],  # "Over" or "Under"
                        'point': convert_floats_to_decimal(outcome.get('point')),
                        'price': convert_floats_to_decimal(outcome['price']),
                        'commence_time': props_data['commence_time'],
                        'bet_type': 'PROP',
                        'updated_at': timestamp,
                        'ttl': ttl
                    }
                    
                    # Store historical snapshot
                    self.table.put_item(Item={**item_data, 'sk': sk_historical})
                    
                    # Store/update latest pointer for frontend
                    self.table.put_item(Item={**item_data, 'sk': sk_latest, 'latest': True})
                            ':ttl': ttl
                        }
                    )
    
    def store_odds(self, sport: str, odds_data: List[Dict[str, Any]]):
        """Store odds in DynamoDB with normalized schema (one item per bookmaker per market)"""
        # Collect from ALL bookmakers for better prediction accuracy
        # Frontend will filter to display only specific bookmakers
        
        for game in odds_data:
            game_id = game['id']
            
            for bookmaker in game['bookmakers']:
                    
                for market in bookmaker['markets']:
                    # Create timestamped sort key for historical tracking
                    timestamp = datetime.utcnow().isoformat()
                    sk_historical = f"{bookmaker['key']}#{market['key']}#{timestamp}"
                    sk_latest = f"{bookmaker['key']}#{market['key']}#LATEST"
                    pk = f"GAME#{game_id}"
                    
                    # Calculate TTL (2 days after game commence time)
                    commence_dt = datetime.fromisoformat(game['commence_time'].replace('Z', '+00:00'))
                    ttl = int((commence_dt + timedelta(days=2)).timestamp())
                    
                    item_data = {
                        'pk': pk,
                        'sport': sport,
                        'home_team': game['home_team'],
                        'away_team': game['away_team'],
                        'commence_time': game['commence_time'],
                        'market_key': market['key'],
                        'bookmaker': bookmaker['key'],
                        'outcomes': convert_floats_to_decimal(market['outcomes']),
                        'bet_type': 'GAME',
                        'updated_at': timestamp,
                        'ttl': ttl
                    }
                    
                    # Store historical snapshot
                    self.table.put_item(Item={**item_data, 'sk': sk_historical})
                    
                    # Store/update latest pointer for frontend
                    self.table.put_item(Item={**item_data, 'sk': sk_latest, 'latest': True})
    
    def collect_all_odds(self):
        """Main method to collect odds for all active sports"""
        active_sports = self.get_active_sports()
        print(f"Active sports: {active_sports}")
        
        total_games = 0
        total_props = 0
        for sport in active_sports:
            print(f"Collecting odds for {sport}...")
            odds = self.get_odds(sport)
            self.store_odds(sport, odds)
            total_games += len(odds)
            print(f"Stored {len(odds)} games for {sport}")
            
            # Collect player props for each game
            for game in odds:
                try:
                    props = self.get_player_props(sport, game['id'])
                    if props.get('bookmakers'):
                        self.store_player_props(sport, game['id'], props)
                        total_props += len(props.get('bookmakers', []))
                except Exception as e:
                    print(f"Error collecting props for game {game['id']}: {str(e)}")
        
        print(f"Collected {total_props} player prop bookmakers")
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
