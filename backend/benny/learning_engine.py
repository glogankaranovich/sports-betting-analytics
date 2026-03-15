"""Learning engine for adaptive betting strategy"""
from typing import Dict, Any
from boto3.dynamodb.conditions import Key


class LearningEngine:
    """Manages adaptive thresholds and performance tracking"""

    BASE_MIN_CONFIDENCE = 0.70
    GAME_MARKET_CONFIDENCE = 0.80
    PROP_MARKET_CONFIDENCE = 0.65
    GAME_MARKETS = {"h2h", "spread", "spreads", "total", "totals"}
    MIN_SAMPLE_SIZE = 30
    ROI_BLOCK_THRESHOLD = -0.10  # Block markets with worse than -10% ROI
    ROI_PENALTY_THRESHOLD = -0.03  # Raise threshold for markets with -3% to -10% ROI
    ROI_MIN_SAMPLE = 20  # Need 20+ settled bets before ROI gating kicks in

    def __init__(self, table, pk="BENNY"):
        self.table = table
        self.pk = pk
        self.params = self._load_parameters()

    def _load_parameters(self) -> Dict[str, Any]:
        """Load learning parameters from DynamoDB"""
        response = self.table.get_item(
            Key={"pk": f"{self.pk}#LEARNING", "sk": "PARAMETERS"}
        )
        return response.get(
            "Item", {"pk": f"{self.pk}#LEARNING", "sk": "PARAMETERS", "performance_by_sport": {}, "performance_by_market": {}}
        )

    def get_adaptive_threshold(self, sport: str, market: str) -> float:
        """Calculate confidence threshold based on learned optimal thresholds,
        falling back to market-type defaults (0.80 game, 0.65 props).
        Auto-raises threshold or blocks markets with negative ROI."""
        # Check ROI-based gating first
        market_perf = self.params.get("performance_by_market", {}).get(market, {})
        if market_perf.get("total", 0) >= self.ROI_MIN_SAMPLE:
            wagered = float(market_perf.get("wagered", 0))
            returned = float(market_perf.get("returned", 0))
            if wagered > 0:
                market_roi = (returned - wagered) / wagered
                if market_roi <= self.ROI_BLOCK_THRESHOLD:
                    print(f"[LEARNING] PROBATION {market}: ROI={market_roi:.1%} after {market_perf['total']} bets — threshold=0.85")
                    return 0.85  # Probation: high bar, but still allows strong conviction bets
                elif market_roi <= self.ROI_PENALTY_THRESHOLD:
                    penalty = min(0.10, abs(market_roi))  # Up to +10% confidence penalty
                    base = self.GAME_MARKET_CONFIDENCE if market in self.GAME_MARKETS else self.PROP_MARKET_CONFIDENCE
                    penalized = min(base + penalty, 0.95)
                    print(f"[LEARNING] Penalizing {market}: ROI={market_roi:.1%}, threshold {base}->{penalized:.2f}")
                    return penalized

        # Try learned optimal thresholds
        try:
            response = self.table.get_item(
                Key={"pk": f"{self.pk}#LEARNING", "sk": "THRESHOLDS"}
            )
            thresholds = response.get("Item", {}).get("thresholds", {})

            if sport in thresholds.get("by_sport", {}):
                return thresholds["by_sport"][sport]["optimal_min_confidence"]

            if market in thresholds.get("by_market", {}):
                return thresholds["by_market"][market]["optimal_min_confidence"]

            if "global" in thresholds:
                return thresholds["global"]["optimal_min_confidence"]
        except:
            pass

        # Fallback: market-type-aware defaults
        if market in self.GAME_MARKETS:
            return self.GAME_MARKET_CONFIDENCE
        return self.PROP_MARKET_CONFIDENCE

    def get_performance_warnings(self, current_sport: str = None) -> str:
        """Generate performance warnings for AI decision-making"""
        warnings = []

        for sport, perf in self.params.get("performance_by_sport", {}).items():
            if perf.get("total", 0) >= self.MIN_SAMPLE_SIZE:
                win_rate = perf["wins"] / perf["total"]
                record = f"{perf['wins']}-{perf['total'] - perf['wins']}"

                if win_rate < 0.35:
                    warnings.append(
                        f"⚠️ {sport.upper()}: {win_rate:.1%} ({record}) - STRUGGLE here, be EXTREMELY cautious"
                    )
                elif win_rate < 0.45:
                    warnings.append(
                        f"⚠️ {sport.upper()}: {win_rate:.1%} ({record}) - Underperform here, be cautious"
                    )
                elif win_rate > 0.55:
                    warnings.append(
                        f"✅ {sport.upper()}: {win_rate:.1%} ({record}) - EXCEL here"
                    )

        for market, perf in self.params.get("performance_by_market", {}).items():
            if perf.get("total", 0) >= self.MIN_SAMPLE_SIZE:
                win_rate = perf["wins"] / perf["total"]
                record = f"{perf['wins']}-{perf['total'] - perf['wins']}"
                wagered = float(perf.get("wagered", 0))
                returned = float(perf.get("returned", 0))
                roi = (returned - wagered) / wagered if wagered > 0 else 0

                if roi <= self.ROI_BLOCK_THRESHOLD:
                    warnings.append(
                        f"🚫 {market}: {win_rate:.1%} ({record}), ROI={roi:.1%} - PROBATION (only bet with 90%+ confidence)"
                    )
                elif roi <= self.ROI_PENALTY_THRESHOLD:
                    warnings.append(
                        f"⚠️ {market}: {win_rate:.1%} ({record}), ROI={roi:.1%} - Threshold raised"
                    )
                elif win_rate < 0.45:
                    warnings.append(
                        f"⚠️ {market}: {win_rate:.1%} ({record}) - Avoid unless exceptional"
                    )
                elif win_rate > 0.55:
                    warnings.append(
                        f"✅ {market}: {win_rate:.1%} ({record}), ROI={roi:+.1%} - Strong performance"
                    )

        return (
            "YOUR TRACK RECORD:\n" + "\n".join(warnings)
            if warnings
            else "YOUR TRACK RECORD: Insufficient data"
        )
