"""Dynamic model weighting based on recent performance."""
import os
from datetime import datetime, timedelta
import boto3
from boto3.dynamodb.conditions import Key


class DynamicModelWeighting:
    """Weight models based on actual ROI per sport."""

    def __init__(self, lookback_days=90):
        self.lookback_days = lookback_days
        table_name = os.environ.get("DYNAMODB_TABLE", "carpool-bets-v2-dev")
        self.dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        self.table = self.dynamodb.Table(table_name)

    def get_model_weights(self, sport, bet_type="game", models=None):
        """Calculate weights dynamically from actual performance."""
        if models is None:
            models = ["consensus", "value", "momentum", "contrarian", "hot_cold", 
                     "rest_schedule", "matchup", "injury_aware", "fundamentals"]

        cutoff = (datetime.utcnow() - timedelta(days=self.lookback_days)).isoformat()
        
        # Calculate ROI for each model
        performances = {}
        for model in models:
            pk = f"VERIFIED#{model}#{sport}#{bet_type}"
            
            try:
                response = self.table.query(
                    IndexName='VerifiedAnalysisGSI',
                    KeyConditionExpression=Key('verified_analysis_pk').eq(pk) & Key('verified_analysis_sk').gte(cutoff)
                )
                
                items = response.get('Items', [])
                if len(items) < 20:
                    performances[model] = 0.0  # Not enough data
                    continue
                
                # Calculate ROI
                correct = sum(1 for i in items if i.get('analysis_correct'))
                total = len(items)
                
                # Assume -110 odds: win = +90.91, loss = -110
                profit = (correct * 90.91) - ((total - correct) * 110)
                wagered = total * 110
                roi = profit / wagered if wagered > 0 else 0
                
                performances[model] = max(0, roi)  # Exclude negative ROI
                
            except Exception as e:
                print(f"Error calculating performance for {model}: {e}")
                performances[model] = 0.0
        
        # Normalize to weights
        total = sum(performances.values())
        if total == 0:
            return {m: 1.0 / len(models) for m in models}

        weights = {m: p / total for m, p in performances.items()}
        return weights
