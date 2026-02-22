"""Dynamic model weighting based on recent performance."""
import os


class DynamicModelWeighting:
    """Weight models based on recent accuracy."""

    def __init__(self, lookback_days=30):
        self.lookback_days = lookback_days
        from model_performance import ModelPerformanceTracker
        table_name = os.environ.get("DYNAMODB_TABLE", "sports-betting-bets-dev")
        self.tracker = ModelPerformanceTracker(table_name)

    def get_model_weights(self, sport, bet_type="game", models=None):
        """Calculate dynamic weights for multiple models based on recent performance."""
        if models is None:
            models = ["consensus", "value", "momentum", "contrarian", "hot_cold", 
                     "rest_schedule", "matchup", "injury_aware", "fundamentals"]

        performances = {}
        
        for model in models:
            perf = self.tracker.get_model_performance(model, sport, days=self.lookback_days)
            
            # If no data or insufficient samples, use neutral weight
            if perf["total_predictions"] < 10:
                performances[model] = 0.5
            else:
                # Weight by accuracy
                performances[model] = perf["accuracy"]

        # Normalize to weights
        total = sum(performances.values())
        if total == 0:
            # Equal weights if no performance data
            return {m: 1.0 / len(models) for m in models}

        weights = {m: p / total for m, p in performances.items()}
        return weights
