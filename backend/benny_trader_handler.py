"""Lambda handler for Benny autonomous trader."""
import json
import os
from datetime import datetime
from benny_trader import BennyTrader


def handler(event, context):
    """
    Scheduled Lambda handler that runs Benny trader daily.
    Analyzes upcoming games and places virtual bets.
    """
    table_name = os.environ["BETS_TABLE"]
    trader = BennyTrader(table_name)

    results = trader.run_daily_analysis()

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Benny trader executed successfully",
                "bets_placed": results.get("bets_placed", 0),
                "games_analyzed": results.get("opportunities_found", 0),
                "current_bankroll": float(results.get("remaining_bankroll", 0)),
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
    }
