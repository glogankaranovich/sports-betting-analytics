"""Bet execution and notification handling"""
import json
import os
from datetime import datetime
from decimal import Decimal
from typing import Dict, Any


class BetExecutor:
    """Handles bet placement and notifications"""
    
    def __init__(self, table, sqs_client, notification_queue_url=None):
        self.table = table
        self.sqs = sqs_client
        self.notification_queue_url = notification_queue_url
    
    def place_bet(self, opportunity: Dict[str, Any], bet_size: Decimal, bankroll: Decimal) -> Dict[str, Any]:
        """Place a bet and store in DynamoDB"""
        bet_id = f"{datetime.utcnow().isoformat()}#{opportunity['game_id']}"
        
        bet = {
            "pk": "BENNY",
            "sk": f"BET#{bet_id}",
            "GSI1PK": "BENNY#BETS",
            "GSI1SK": opportunity["commence_time"],
            "bet_id": bet_id,
            "game_id": opportunity["game_id"],
            "sport": opportunity["sport"],
            "home_team": opportunity["home_team"],
            "away_team": opportunity["away_team"],
            "prediction": opportunity["prediction"],
            "confidence": Decimal(str(opportunity["confidence"])),
            "ai_reasoning": opportunity["reasoning"],
            "ai_key_factors": opportunity["key_factors"],
            "bet_amount": bet_size,
            "market_key": opportunity["market_key"],
            "commence_time": opportunity["commence_time"],
            "placed_at": datetime.utcnow().isoformat(),
            "status": "pending",
            "bankroll_before": bankroll,
            "odds": Decimal(str(opportunity.get("odds", 0))) if opportunity.get("odds") else None,
        }
        
        self.table.put_item(Item=bet)
        
        # Store analysis record
        analysis_record = {
            "pk": f"ANALYSIS#{opportunity['sport']}#{opportunity['game_id']}#fanduel",
            "sk": "benny#game#LATEST",
            "model": "benny",
            "analysis_type": "game",
            "sport": opportunity["sport"],
            "bookmaker": "fanduel",
            "game_id": opportunity["game_id"],
            "home_team": opportunity["home_team"],
            "away_team": opportunity["away_team"],
            "prediction": opportunity["prediction"],
            "confidence": Decimal(str(opportunity["confidence"])),
            "reasoning": opportunity["reasoning"],
            "market_key": opportunity["market_key"],
            "commence_time": opportunity["commence_time"],
            "created_at": datetime.utcnow().isoformat(),
            "latest": True,
        }
        self.table.put_item(Item=analysis_record)
        
        # Send notification
        self._send_notification(bet, opportunity)
        
        return {
            "success": True,
            "bet_id": bet_id,
            "bet_amount": float(bet_size),
            "ai_reasoning": opportunity["reasoning"],
        }
    
    def _send_notification(self, bet: Dict, opportunity: Dict):
        """Send bet notification to SQS"""
        environment = os.environ.get('ENVIRONMENT', 'dev')
        if environment != 'dev' or not self.notification_queue_url:
            return
        
        message = {
            'type': 'bet_placed',
            'data': {
                'sport': opportunity['sport'],
                'game': f"{opportunity['away_team']} @ {opportunity['home_team']}",
                'market_key': opportunity['market_key'],
                'pick': opportunity['prediction'],
                'odds': float(opportunity.get('odds', 0)),
                'confidence': float(opportunity['confidence']),
                'stake': float(bet['bet_amount']),
                'bankroll_percentage': float(bet['bet_amount'] / bet['bankroll_before']),
                'expected_roi': float(opportunity.get('expected_value', 0)),
                'reasoning': opportunity['reasoning']
            }
        }
        
        try:
            self.sqs.send_message(
                QueueUrl=self.notification_queue_url,
                MessageBody=json.dumps(message)
            )
        except Exception as e:
            print(f"Failed to send notification: {e}")
