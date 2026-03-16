"""Bet outcome analyzer - finds feature correlations with wins"""
from typing import Dict, Any, List
from collections import defaultdict
from boto3.dynamodb.conditions import Key
from benny.threshold_optimizer import _to_decimal


class OutcomeAnalyzer:
    """Analyzes settled bets to find which features predict wins"""
    
    def __init__(self, table, pk="BENNY"):
        self.table = table
        self.pk = pk

    def analyze_features(self) -> Dict[str, Any]:
        """Analyze feature correlations with wins"""
        # Get all settled bets with features
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(self.pk) & Key("sk").begins_with("BET#"),
            FilterExpression="attribute_exists(features) AND #status IN (:won, :lost)",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":won": "won", ":lost": "lost"}
        )
        
        bets = response.get("Items", [])
        
        if len(bets) < 10:
            return {"error": "Insufficient data", "bet_count": len(bets)}
        
        # Analyze each feature
        insights = {
            "elo_diff": self._analyze_numeric_feature(bets, "elo_diff", bins=[(-1000, -100), (-100, -50), (-50, 0), (0, 50), (50, 100), (100, 1000)]),
            "fatigue_score": self._analyze_numeric_feature(bets, "fatigue_score", bins=[(0, 30), (30, 60), (60, 100)]),
            "injury_advantage": self._analyze_numeric_feature(bets, "injury_advantage", bins=[(-5, -1), (-1, 0), (0, 1), (1, 5)]),
            "form_advantage": self._analyze_numeric_feature(bets, "form_advantage", bins=[(-5, -2), (-2, 0), (0, 2), (2, 5)]),
            "is_home": self._analyze_categorical_feature(bets, "is_home"),
            "is_favorite": self._analyze_categorical_feature(bets, "is_favorite"),
            "market_type": self._analyze_categorical_feature(bets, "market_type"),
            "sport": self._analyze_categorical_feature(bets, "sport"),
        }
        
        # Find strongest predictors
        strongest = self._rank_features(insights)
        
        return {
            "total_bets": len(bets),
            "insights": insights,
            "strongest_predictors": strongest
        }
    
    def analyze_confidence_calibration(self) -> Dict[str, Any]:
        """Analyze if AI confidence scores are calibrated with actual win rates"""
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(self.pk) & Key("sk").begins_with("BET#"),
            FilterExpression="#status = :settled",
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={":settled": "settled"}
        )
        
        bets = response.get("Items", [])
        
        if len(bets) < 20:
            return {"error": "Insufficient data", "bet_count": len(bets)}
        
        # Group by confidence buckets
        buckets = {
            "65-70": [],
            "70-75": [],
            "75-80": [],
            "80-85": [],
            "85-90": [],
            "90-95": [],
            "95-100": []
        }
        
        for bet in bets:
            confidence = float(bet.get("confidence", 0))
            if confidence < 0.65:
                continue
            
            if 0.65 <= confidence < 0.70:
                buckets["65-70"].append(bet)
            elif 0.70 <= confidence < 0.75:
                buckets["70-75"].append(bet)
            elif 0.75 <= confidence < 0.80:
                buckets["75-80"].append(bet)
            elif 0.80 <= confidence < 0.85:
                buckets["80-85"].append(bet)
            elif 0.85 <= confidence < 0.90:
                buckets["85-90"].append(bet)
            elif 0.90 <= confidence < 0.95:
                buckets["90-95"].append(bet)
            else:
                buckets["95-100"].append(bet)
        
        # Calculate actual win rate per bucket
        calibration = {}
        for bucket_name, bucket_bets in buckets.items():
            if not bucket_bets:
                continue
            
            wins = sum(1 for b in bucket_bets if b.get("result") == "win")
            win_rate = wins / len(bucket_bets)
            
            # Expected confidence (midpoint of bucket)
            bucket_min = float(bucket_name.split("-")[0]) / 100
            bucket_max = float(bucket_name.split("-")[1]) / 100
            expected_confidence = (bucket_min + bucket_max) / 2
            
            calibration[bucket_name] = {
                "count": len(bucket_bets),
                "wins": wins,
                "actual_win_rate": win_rate,
                "expected_confidence": expected_confidence,
                "calibration_error": abs(win_rate - expected_confidence)
            }
        
        # Calculate overall calibration error
        total_error = sum(c["calibration_error"] * c["count"] for c in calibration.values())
        total_bets = sum(c["count"] for c in calibration.values())
        avg_calibration_error = total_error / total_bets if total_bets > 0 else 0
        
        return {
            "total_bets": len(bets),
            "calibration": calibration,
            "avg_calibration_error": avg_calibration_error,
            "is_well_calibrated": avg_calibration_error < 0.05
        }
    
    def _analyze_numeric_feature(self, bets: List[Dict], feature_name: str, bins: List[tuple]) -> Dict:
        """Analyze numeric feature by binning"""
        results = {}
        
        for bin_min, bin_max in bins:
            bin_bets = []
            for bet in bets:
                features = bet.get("features", {})
                value = features.get(feature_name)
                if value is not None and bin_min <= float(value) < bin_max:
                    bin_bets.append(bet)
            
            if bin_bets:
                wins = sum(1 for b in bin_bets if b.get("result") == "win")
                win_rate = wins / len(bin_bets)
                results[f"{bin_min}_to_{bin_max}"] = {
                    "count": len(bin_bets),
                    "wins": wins,
                    "win_rate": win_rate
                }
        
        return results
    
    def _analyze_categorical_feature(self, bets: List[Dict], feature_name: str) -> Dict:
        """Analyze categorical feature"""
        results = defaultdict(lambda: {"count": 0, "wins": 0})
        
        for bet in bets:
            features = bet.get("features", {})
            value = features.get(feature_name)
            if value is not None:
                key = str(value)
                results[key]["count"] += 1
                if bet.get("result") == "win":
                    results[key]["wins"] += 1
        
        # Calculate win rates
        for key in results:
            count = results[key]["count"]
            wins = results[key]["wins"]
            results[key]["win_rate"] = wins / count if count > 0 else 0
        
        return dict(results)
    
    def _rank_features(self, insights: Dict) -> List[Dict]:
        """Rank features by predictive power (variance in win rates)"""
        rankings = []
        
        for feature, data in insights.items():
            if not data:
                continue
            
            win_rates = [v["win_rate"] for v in data.values() if v.get("count", 0) >= 5]
            if len(win_rates) < 2:
                continue
            
            # Variance as proxy for predictive power
            mean_wr = sum(win_rates) / len(win_rates)
            variance = sum((wr - mean_wr) ** 2 for wr in win_rates) / len(win_rates)
            
            rankings.append({
                "feature": feature,
                "variance": variance,
                "max_win_rate": max(win_rates),
                "min_win_rate": min(win_rates),
                "spread": max(win_rates) - min(win_rates)
            })
        
        return sorted(rankings, key=lambda x: x["spread"], reverse=True)
    
    def save_insights(self, insights: Dict):
        """Save feature insights to DynamoDB"""
        self.table.put_item(Item={
            "pk": f"{self.pk}#LEARNING",
            "sk": "FEATURES",
            "insights": _to_decimal(insights),
            "updated_at": insights.get("timestamp", "")
        })
    
    def save_calibration(self, calibration: Dict):
        """Save confidence calibration to DynamoDB"""
        self.table.put_item(Item={
            "pk": f"{self.pk}#LEARNING",
            "sk": "CALIBRATION",
            "calibration": _to_decimal(calibration),
            "updated_at": calibration.get("timestamp", "")
        })
