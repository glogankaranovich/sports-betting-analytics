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
                "game_bets_placed": results.get("game_bets_placed", 0),
                "prop_bets_placed": results.get("prop_bets_placed", 0),
                "total_bets": results.get("total_bets", 0),
                "game_opportunities": results.get("game_opportunities", 0),
                "prop_opportunities": results.get("prop_opportunities", 0),
                "total_bet_amount": results.get("total_bet_amount", 0),
                "current_bankroll": float(results.get("remaining_bankroll", 0)),
                "timestamp": datetime.utcnow().isoformat(),
            }
        ),
    }
