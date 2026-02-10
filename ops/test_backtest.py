#!/usr/bin/env python3
"""
Test the backtest engine with historical data
"""
import json
import os
import sys
from datetime import datetime, timedelta

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

os.environ['DYNAMODB_TABLE'] = 'carpool-bets-v2-dev'
os.environ['USER_MODELS_TABLE'] = 'Dev-UserModels-UserModels'
os.environ['AWS_PROFILE'] = 'sports-betting-dev'

from backtest_engine import BacktestEngine

# Create a simple test model
test_model_config = {
    "name": "Test Model",
    "sport": "basketball_nba",
    "bet_type": "game",
    "data_sources": {
        "team_stats": {"weight": 0.4},
        "odds_movement": {"weight": 0.3},
        "recent_form": {"weight": 0.3}
    },
    "filters": {
        "min_confidence": 0.6
    }
}

# Test with last 2 weeks
end_date = datetime.utcnow()
start_date = end_date - timedelta(days=14)

print(f"Testing backtest engine...")
print(f"Date range: {start_date.date()} to {end_date.date()}")
print(f"Model config: {json.dumps(test_model_config, indent=2)}")
print("\nRunning backtest...\n")

engine = BacktestEngine()
result = engine.run_backtest(
    user_id="test_user",
    model_id="test_model",
    model_config=test_model_config,
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat()
)

print("=" * 60)
print("BACKTEST RESULTS")
print("=" * 60)
print(json.dumps(result, indent=2, default=str))
