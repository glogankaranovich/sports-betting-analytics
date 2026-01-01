"""
Prediction storage and tracking system
"""

import boto3
import json
from datetime import datetime
from decimal import Decimal
from typing import Dict, List
from ml.models import OddsAnalyzer

class PredictionTracker:
    
    def __init__(self, table_name: str):
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table(table_name)
        self.analyzer = OddsAnalyzer()
    
    def generate_and_store_predictions(self) -> int:
        """Generate predictions for all games and store them"""
        
        # Get all games
        response = self.table.scan()
        games_by_id = {}
        
        print(f"Found {len(response.get('Items', []))} total items")
        
        for item in response.get('Items', []):
            game_id = item.get('pk')  # Use pk instead of game_id
            if game_id and not game_id.startswith('PRED#'):  # Skip existing predictions
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
                    'bookmaker': item.get('sk'),  # Use sk for bookmaker
                    'markets': item.get('markets', [])
                })
        
        print(f"Found {len(games_by_id)} unique games")
        
        # Generate and store predictions
        predictions_stored = 0
        timestamp = datetime.utcnow().isoformat()
        
        for game_data in games_by_id.values():
            try:
                print(f"Processing game: {game_data['home_team']} vs {game_data['away_team']}")
                prediction = self.analyzer.analyze_game(game_data)
                
                # Store prediction
                self.table.put_item(Item={
                    'pk': f"PRED#{game_data['game_id']}",
                    'sk': 'PREDICTION',
                    'game_id': game_data['game_id'],
                    'bookmaker': 'PREDICTION',
                    'prediction_id': f"{game_data['game_id']}#{timestamp}",
                    'sport': game_data['sport'],
                    'home_team': game_data['home_team'],
                    'away_team': game_data['away_team'],
                    'commence_time': game_data['commence_time'],
                    'model_version': 'consensus_v1',
                    'home_win_probability': Decimal(str(prediction.home_win_probability)),
                    'away_win_probability': Decimal(str(prediction.away_win_probability)),
                    'confidence_score': Decimal(str(prediction.confidence_score)),
                    'value_bets': prediction.value_bets,
                    'predicted_at': timestamp,
                    'status': 'pending'  # pending, won, lost
                })
                
                predictions_stored += 1
                print(f"Stored prediction: Home {prediction.home_win_probability}, Away {prediction.away_win_probability}")
                
            except Exception as e:
                print(f"Error processing game: {e}")
                continue
        
        return predictions_stored
    
    def get_predictions(self, limit: int = 50) -> List[Dict]:
        """Get stored predictions"""
        predictions = []
        last_evaluated_key = None
        
        while len(predictions) < limit:
            scan_params = {
                'FilterExpression': boto3.dynamodb.conditions.Attr('pk').begins_with('PRED#'),
                'Limit': min(limit - len(predictions), 100)  # Scan in chunks
            }
            
            if last_evaluated_key:
                scan_params['ExclusiveStartKey'] = last_evaluated_key
                
            response = self.table.scan(**scan_params)
            
            for item in response.get('Items', []):
                predictions.append({
                    'game_id': item.get('game_id', ''),
                    'sport': item.get('sport'),
                    'home_team': item.get('home_team'),
                    'away_team': item.get('away_team'),
                    'commence_time': item.get('commence_time'),
                    'model_version': item.get('model_version'),
                    'home_win_probability': float(item.get('home_win_probability', 0)),
                    'away_win_probability': float(item.get('away_win_probability', 0)),
                    'confidence_score': float(item.get('confidence_score', 0)),
                    'value_bets': item.get('value_bets', []),
                    'predicted_at': item.get('predicted_at'),
                    'status': item.get('status', 'pending')
                })
            
            last_evaluated_key = response.get('LastEvaluatedKey')
            if not last_evaluated_key:
                break
        
        return predictions
