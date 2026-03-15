"""Bankroll management for Benny trader"""
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key


class BankrollManager:
    """Manages bankroll tracking, weekly budget, and bet sizing"""
    
    WEEKLY_BUDGET = Decimal("100.00")
    MAX_BET_PERCENTAGE = 0.20
    
    def __init__(self, table, pk="BENNY"):
        self.table = table
        self.pk = pk
        self.bankroll = self._get_current_bankroll()
        self.week_start = self._get_week_start()
    
    def _get_current_bankroll(self) -> Decimal:
        """Get current bankroll from DynamoDB"""
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(self.pk) & Key("sk").begins_with("BANKROLL#"),
            ScanIndexForward=False,
            Limit=1
        )
        if response["Items"]:
            return Decimal(str(response["Items"][0]["amount"]))
        return self.WEEKLY_BUDGET
    
    def _get_week_start(self) -> datetime:
        """Get start of current betting week (Sunday)"""
        now = datetime.now()
        days_since_sunday = (now.weekday() + 1) % 7
        return (now - timedelta(days=days_since_sunday)).replace(hour=0, minute=0, second=0, microsecond=0)
    
    def update_bankroll(self, new_amount: Decimal):
        """Update bankroll in DynamoDB"""
        timestamp = datetime.now().isoformat()
        
        # Update main bankroll record
        self.table.put_item(Item={
            "pk": self.pk,
            "sk": "BANKROLL",
            "amount": new_amount,
            "updated_at": timestamp
        })
        
        # Create history record
        self.table.put_item(Item={
            "pk": self.pk,
            "sk": f"BANKROLL#{timestamp}",
            "amount": new_amount,
            "updated_at": timestamp
        })
        
        self.bankroll = new_amount
    
    def calculate_bet_size(self, confidence: float, odds: float = None) -> Decimal:
        """Calculate bet size using Kelly Criterion with conservative scaling"""
        if odds is None or odds == 0:
            # Fallback: simple confidence-based sizing
            kelly_pct = (confidence - 0.5) * 2 * 0.25
            bet_size = self.bankroll * Decimal(str(max(0, kelly_pct)))
            max_bet = self.bankroll * Decimal(str(self.MAX_BET_PERCENTAGE))
            return min(bet_size, max_bet)
        
        # Convert American odds to decimal
        if odds > 0:
            decimal_odds = (odds / 100) + 1
        else:
            decimal_odds = (100 / abs(odds)) + 1
        
        # Kelly Criterion
        implied_prob = Decimal(str(1 / decimal_odds))
        edge = Decimal(str(confidence)) - implied_prob
        kelly_fraction = edge / (Decimal(str(decimal_odds)) - 1)
        conservative_kelly = max(0, kelly_fraction * Decimal('0.25'))
        
        bet_size = self.bankroll * conservative_kelly
        max_bet = self.bankroll * Decimal(str(self.MAX_BET_PERCENTAGE))
        return min(bet_size, max_bet)
    
    def get_bankroll_history(self) -> List[Dict[str, Any]]:
        """Get bankroll history"""
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq("BENNY") & Key("sk").begins_with("BANKROLL#"),
            ScanIndexForward=False,
            Limit=50
        )
        return [{"timestamp": item["timestamp"], "amount": float(item["amount"])} 
                for item in response["Items"]]
    
    def should_reset_weekly_budget(self) -> bool:
        """Check if we should reset to weekly budget"""
        return self.bankroll <= 0
    
    def reset_weekly_budget(self):
        """Reset bankroll to weekly budget"""
        self.update_bankroll(self.WEEKLY_BUDGET)
