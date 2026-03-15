"""Dynamic threshold optimizer - finds optimal betting thresholds"""
import json
from decimal import Decimal
from typing import Dict, Any, List, Tuple
from boto3.dynamodb.conditions import Key


def _to_decimal(obj):
    """Recursively convert floats/ints to Decimal for DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, int) and not isinstance(obj, bool):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_to_decimal(i) for i in obj]
    return obj


class ThresholdOptimizer:
    """Optimizes min_confidence and min_ev thresholds to maximize ROI"""
    
    def __init__(self, table, pk="BENNY_V2"):
        self.table = table
        self.pk = pk
    
    def optimize_thresholds(self) -> Dict[str, Any]:
        """Find optimal thresholds per sport/market"""
        # Get all settled bets
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(self.pk) & Key("sk").begins_with("BET#"),
            FilterExpression="#status IN (:won, :lost)",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":won": "won", ":lost": "lost"}
        )
        
        bets = response.get("Items", [])
        
        if len(bets) < 30:
            return {"error": "Insufficient data", "bet_count": len(bets)}
        
        # Optimize globally
        global_optimal = self._find_optimal_thresholds(bets)
        
        # Optimize per sport
        sport_optimal = {}
        for sport in set(b.get("sport") for b in bets):
            sport_bets = [b for b in bets if b.get("sport") == sport]
            if len(sport_bets) >= 10:
                sport_optimal[sport] = self._find_optimal_thresholds(sport_bets)
        
        # Optimize per market
        market_optimal = {}
        for market in set(b.get("market_key") for b in bets):
            market_bets = [b for b in bets if b.get("market_key") == market]
            if len(market_bets) >= 10:
                market_optimal[market] = self._find_optimal_thresholds(market_bets)
        
        return {
            "total_bets": len(bets),
            "global": global_optimal,
            "by_sport": sport_optimal,
            "by_market": market_optimal
        }
    
    def _find_optimal_thresholds(self, bets: List[Dict]) -> Dict[str, Any]:
        """Find optimal confidence and EV thresholds for a set of bets"""
        # Test different confidence thresholds
        confidence_thresholds = [0.65, 0.70, 0.75, 0.80, 0.85]
        ev_thresholds = [0.03, 0.05, 0.08, 0.10, 0.12]
        
        best_roi = -float('inf')
        best_conf = 0.70
        best_ev = 0.05
        best_stats = {}
        
        for conf_threshold in confidence_thresholds:
            for ev_threshold in ev_thresholds:
                # Filter bets that would pass these thresholds
                filtered_bets = [
                    b for b in bets
                    if float(b.get("confidence", 0)) >= conf_threshold
                ]
                
                if len(filtered_bets) < 5:
                    continue
                
                # Calculate ROI for this threshold combination
                total_wagered = sum(float(b.get("bet_amount", 0)) for b in filtered_bets)
                total_profit = sum(float(b.get("profit", 0)) for b in filtered_bets)
                roi = (total_profit / total_wagered) if total_wagered > 0 else 0
                
                wins = sum(1 for b in filtered_bets if b.get("status") == "won")
                win_rate = wins / len(filtered_bets)
                
                # Update best if this is better
                if roi > best_roi:
                    best_roi = roi
                    best_conf = conf_threshold
                    best_ev = ev_threshold
                    best_stats = {
                        "roi": roi,
                        "win_rate": win_rate,
                        "bet_count": len(filtered_bets),
                        "total_wagered": total_wagered,
                        "total_profit": total_profit
                    }
        
        return {
            "optimal_min_confidence": best_conf,
            "optimal_min_ev": best_ev,
            "expected_roi": best_roi,
            "expected_win_rate": best_stats.get("win_rate", 0),
            "sample_size": best_stats.get("bet_count", 0)
        }
    
    def save_optimal_thresholds(self, thresholds: Dict):
        """Save optimal thresholds to DynamoDB"""
        self.table.put_item(Item={
            "pk": f"{self.pk}#LEARNING",
            "sk": "THRESHOLDS",
            "thresholds": _to_decimal(thresholds),
            "updated_at": thresholds.get("timestamp", "")
        })
