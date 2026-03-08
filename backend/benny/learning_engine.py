"""Learning engine for adaptive betting strategy"""
from typing import Dict, Any
from boto3.dynamodb.conditions import Key


class LearningEngine:
    """Manages adaptive thresholds and performance tracking"""
    
    BASE_MIN_CONFIDENCE = 0.70
    MIN_SAMPLE_SIZE = 30
    
    def __init__(self, table):
        self.table = table
        self.params = self._load_parameters()
    
    def _load_parameters(self) -> Dict[str, Any]:
        """Load learning parameters from DynamoDB"""
        response = self.table.get_item(Key={"pk": "BENNY#LEARNING", "sk": "PARAMETERS"})
        return response.get("Item", {
            "performance_by_sport": {},
            "performance_by_market": {}
        })
    
    def get_adaptive_threshold(self, sport: str, market: str) -> float:
        """Calculate confidence threshold based on historical performance"""
        sport_perf = self.params.get('performance_by_sport', {}).get(sport, {})
        market_perf = self.params.get('performance_by_market', {}).get(market, {})
        
        sport_win_rate = None
        if sport_perf.get('total', 0) >= self.MIN_SAMPLE_SIZE:
            sport_win_rate = sport_perf['wins'] / sport_perf['total']
        
        market_win_rate = None
        if market_perf.get('total', 0) >= self.MIN_SAMPLE_SIZE:
            market_win_rate = market_perf['wins'] / market_perf['total']
        
        if sport_win_rate is None and market_win_rate is None:
            return self.BASE_MIN_CONFIDENCE
        
        worst_win_rate = min([r for r in [sport_win_rate, market_win_rate] if r is not None], default=0.50)
        
        if worst_win_rate < 0.35:
            return 0.80
        elif worst_win_rate < 0.45:
            return 0.75
        elif worst_win_rate > 0.55:
            return 0.65
        else:
            return 0.70
    
    def get_performance_warnings(self, current_sport: str = None) -> str:
        """Generate performance warnings for AI decision-making"""
        warnings = []
        
        for sport, perf in self.params.get('performance_by_sport', {}).items():
            if perf.get('total', 0) >= self.MIN_SAMPLE_SIZE:
                win_rate = perf['wins'] / perf['total']
                record = f"{perf['wins']}-{perf['total'] - perf['wins']}"
                
                if win_rate < 0.35:
                    warnings.append(f"⚠️ {sport.upper()}: {win_rate:.1%} ({record}) - STRUGGLE here, be EXTREMELY cautious")
                elif win_rate < 0.45:
                    warnings.append(f"⚠️ {sport.upper()}: {win_rate:.1%} ({record}) - Underperform here, be cautious")
                elif win_rate > 0.55:
                    warnings.append(f"✅ {sport.upper()}: {win_rate:.1%} ({record}) - EXCEL here")
        
        for market, perf in self.params.get('performance_by_market', {}).items():
            if perf.get('total', 0) >= self.MIN_SAMPLE_SIZE:
                win_rate = perf['wins'] / perf['total']
                record = f"{perf['wins']}-{perf['total'] - perf['wins']}"
                
                if win_rate < 0.45:
                    warnings.append(f"⚠️ {market}: {win_rate:.1%} ({record}) - Avoid unless exceptional")
                elif win_rate > 0.55:
                    warnings.append(f"✅ {market}: {win_rate:.1%} ({record}) - Strong performance")
        
        return "YOUR TRACK RECORD:\n" + "\n".join(warnings) if warnings else "YOUR TRACK RECORD: Insufficient data"
