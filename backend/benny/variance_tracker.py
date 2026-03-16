"""Monte Carlo variance tracker for Benny"""
import random
from decimal import Decimal
from typing import Dict, Any, List
from boto3.dynamodb.conditions import Key


class VarianceTracker:
    """Simulates bankroll paths to understand expected variance"""

    SIMULATIONS = 1000

    def __init__(self, table, pk="BENNY_V3"):
        self.table = table
        self.pk = pk

    def run_simulation(self) -> Dict[str, Any]:
        """Run Monte Carlo simulation based on actual bet history"""
        bets = self._get_settled_bets()
        if len(bets) < 20:
            return {"error": "Need 20+ settled bets", "bet_count": len(bets)}

        # Extract actual distributions
        win_rate = sum(1 for b in bets if b.get("status") == "won") / len(bets)
        bet_sizes = [float(b.get("bet_amount", 0)) for b in bets]
        avg_bet = sum(bet_sizes) / len(bet_sizes)

        # Get payout multipliers from winning bets
        won_bets = [b for b in bets if b.get("status") == "won"]
        if won_bets:
            payouts = [float(b.get("payout", 0)) / float(b.get("bet_amount", 1)) for b in won_bets if float(b.get("bet_amount", 0)) > 0]
            avg_payout = sum(payouts) / len(payouts) if payouts else 1.9
        else:
            avg_payout = 1.9

        # Simulate N bankroll paths for the same number of bets
        num_bets = len(bets)
        final_profits = []

        for _ in range(self.SIMULATIONS):
            profit = 0.0
            for _ in range(num_bets):
                if random.random() < win_rate:
                    profit += avg_bet * (avg_payout - 1)
                else:
                    profit -= avg_bet
            final_profits.append(profit)

        final_profits.sort()
        actual_profit = sum(float(b.get("profit", 0)) for b in bets)
        actual_wagered = sum(float(b.get("bet_amount", 0)) for b in bets)

        # Calculate percentiles
        p5 = final_profits[int(self.SIMULATIONS * 0.05)]
        p25 = final_profits[int(self.SIMULATIONS * 0.25)]
        p50 = final_profits[int(self.SIMULATIONS * 0.50)]
        p75 = final_profits[int(self.SIMULATIONS * 0.75)]
        p95 = final_profits[int(self.SIMULATIONS * 0.95)]

        # Where does actual result fall?
        percentile = sum(1 for p in final_profits if p <= actual_profit) / self.SIMULATIONS

        # How many more bets needed for significance?
        # Rule of thumb: need 1/(edge^2) bets. With ~1% edge, need ~10000.
        # More practical: 95% CI narrows as sqrt(n). Need CI to exclude 0.
        edge = win_rate * avg_payout - 1
        if edge > 0:
            # Approximate bets needed for 95% significance
            variance_per_bet = (avg_payout ** 2) * win_rate * (1 - win_rate)
            bets_for_significance = int((1.96 ** 2 * variance_per_bet) / (edge ** 2)) if edge > 0 else 9999
        else:
            bets_for_significance = 9999

        return {
            "total_bets": num_bets,
            "win_rate": round(win_rate, 4),
            "avg_bet_size": round(avg_bet, 2),
            "avg_payout_multiplier": round(avg_payout, 3),
            "actual_profit": round(actual_profit, 2),
            "actual_roi": round(actual_profit / actual_wagered, 4) if actual_wagered > 0 else 0,
            "simulated_percentiles": {
                "p5": round(p5, 2),
                "p25": round(p25, 2),
                "p50": round(p50, 2),
                "p75": round(p75, 2),
                "p95": round(p95, 2),
            },
            "actual_percentile": round(percentile, 2),
            "is_within_expected": 0.05 <= percentile <= 0.95,
            "bets_for_significance": min(bets_for_significance, 9999),
            "edge_estimate": round(edge, 4),
        }

    def _get_settled_bets(self) -> List[Dict]:
        response = self.table.query(
            KeyConditionExpression=Key("pk").eq(self.pk) & Key("sk").begins_with("BET#"),
            FilterExpression="#s IN (:w, :l)",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":w": "won", ":l": "lost"},
        )
        return response.get("Items", [])

    def save_simulation(self, results: Dict):
        from datetime import datetime
        from benny.threshold_optimizer import _to_decimal
        self.table.put_item(Item={
            "pk": f"{self.pk}#LEARNING",
            "sk": "VARIANCE",
            **_to_decimal(results),
            "updated_at": datetime.utcnow().isoformat(),
        })
