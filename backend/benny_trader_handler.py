"""Lambda handler for Benny autonomous trader."""
import json
import os
from datetime import datetime
from benny_trader import BennyTrader


def handler(event, context):
    """
    Scheduled Lambda handler that runs Benny trader daily.
    Analyzes upcoming games and places virtual bets.
    Runs v1 and v3 for A/B testing.
    """
    table_name = os.environ["BETS_TABLE"]
    
    # Run v1 (Kelly sizing, full prompts)
    print("Running Benny v1...")
    trader_v1 = BennyTrader(table_name, version="v1")
    results_v1 = trader_v1.run_daily_analysis()
    
    # Run v3 (flat sizing, lean prompts)
    print("Running Benny v3...")
    trader_v3 = BennyTrader(table_name, version="v3")
    results_v3 = trader_v3.run_daily_analysis()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Benny trader executed successfully (v1 + v3)",
                "v1": {
                    "game_bets_placed": results_v1.get("game_bets_placed", 0),
                    "prop_bets_placed": results_v1.get("prop_bets_placed", 0),
                    "total_bets": results_v1.get("total_bets", 0),
                    "current_bankroll": float(results_v1.get("remaining_bankroll", 0)),
                },
                "v3": {
                    "game_bets_placed": results_v3.get("game_bets_placed", 0),
                    "prop_bets_placed": results_v3.get("prop_bets_placed", 0),
                    "total_bets": results_v3.get("total_bets", 0),
                    "current_bankroll": float(results_v3.get("remaining_bankroll", 0)),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
    }
