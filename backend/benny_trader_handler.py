"""Lambda handler for Benny autonomous trader."""
import json
import os
from datetime import datetime
from benny_trader import BennyTrader


def handler(event, context):
    """
    Scheduled Lambda handler that runs Benny trader daily.
    Analyzes upcoming games and places virtual bets.
    Runs both v1 and v2 in parallel for A/B testing.
    """
    table_name = os.environ["BETS_TABLE"]
    
    # Run v1 (current version)
    print("Running Benny v1...")
    trader_v1 = BennyTrader(table_name, version="v1")
    results_v1 = trader_v1.run_daily_analysis()
    
    # Run v2 (learning version)
    print("Running Benny v2...")
    trader_v2 = BennyTrader(table_name, version="v2")
    results_v2 = trader_v2.run_daily_analysis()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Benny trader executed successfully (both versions)",
                "v1": {
                    "game_bets_placed": results_v1.get("game_bets_placed", 0),
                    "prop_bets_placed": results_v1.get("prop_bets_placed", 0),
                    "total_bets": results_v1.get("total_bets", 0),
                    "current_bankroll": float(results_v1.get("remaining_bankroll", 0)),
                },
                "v2": {
                    "game_bets_placed": results_v2.get("game_bets_placed", 0),
                    "prop_bets_placed": results_v2.get("prop_bets_placed", 0),
                    "total_bets": results_v2.get("total_bets", 0),
                    "current_bankroll": float(results_v2.get("remaining_bankroll", 0)),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
    }
