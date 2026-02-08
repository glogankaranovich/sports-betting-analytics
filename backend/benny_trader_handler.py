"""Lambda handler for Benny autonomous trader."""
import json
import os
from datetime import datetime, timedelta
from benny_trader import BennyTrader


def handler(event, context):
    """
    Scheduled Lambda handler that runs Benny trader daily.
    Analyzes upcoming games and places virtual bets.
    """
    table_name = os.environ["BETS_TABLE"]
    trader = BennyTrader(table_name)

    # Analyze games for next 24 hours
    now = datetime.utcnow()
    end_time = now + timedelta(hours=24)

    results = trader.analyze_and_bet(start_time=now, end_time=end_time)

    return {
        "statusCode": 200,
        "body": json.dumps(
            {
                "message": "Benny trader executed successfully",
                "bets_placed": results["bets_placed"],
                "games_analyzed": results["games_analyzed"],
                "current_bankroll": results["current_bankroll"],
                "timestamp": now.isoformat(),
            }
        ),
    }
