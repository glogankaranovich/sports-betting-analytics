"""Parlay engine: builds 2-3 leg parlays from uncorrelated prop opportunities."""

from decimal import Decimal
from itertools import combinations
from typing import Any, Dict, List


class ParlayEngine:
    MAX_LEGS = 3
    MIN_LEGS = 2
    MIN_LEG_CONFIDENCE = 0.70
    KELLY_FRACTION = Decimal("0.10")  # More conservative than singles (0.25)
    MAX_BET_PERCENTAGE = Decimal("0.10")  # Cap at 10% of bankroll per parlay

    def build_parlays(
        self, opportunities: List[Dict[str, Any]], max_parlays: int = 3
    ) -> List[Dict[str, Any]]:
        """Build uncorrelated parlays from prop opportunities."""
        # Filter to high-confidence legs only
        legs = [
            o
            for o in opportunities
            if o.get("confidence", 0) >= self.MIN_LEG_CONFIDENCE
        ]
        legs.sort(key=lambda x: x["confidence"], reverse=True)

        parlays = []
        used_legs = set()  # Track indices of legs already in a parlay

        for size in range(self.MAX_LEGS, self.MIN_LEGS - 1, -1):
            for combo in combinations(range(len(legs)), size):
                if len(parlays) >= max_parlays:
                    return parlays
                if any(i in used_legs for i in combo):
                    continue
                selected = [legs[i] for i in combo]
                if not self._legs_uncorrelated(selected):
                    continue

                parlay = self._build_parlay(selected)
                parlays.append(parlay)
                used_legs.update(combo)

        return parlays

    def _legs_uncorrelated(self, legs: List[Dict[str, Any]]) -> bool:
        """Check that no two legs share a game or player."""
        game_ids = [l["game_id"] for l in legs]
        players = [l.get("player") for l in legs]
        # Filter out None/empty players before checking duplicates
        named = [p for p in players if p]
        return len(set(game_ids)) == len(legs) and len(named) == len(set(named))

    def _build_parlay(self, legs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine legs into a parlay with combined odds and probability."""
        combined_prob = 1.0
        combined_decimal_odds = 1.0

        parlay_legs = []
        for leg in legs:
            combined_prob *= leg["confidence"]
            decimal_odds = self._american_to_decimal(float(leg.get("odds", -110)))
            combined_decimal_odds *= decimal_odds
            parlay_legs.append(
                {
                    "game_id": leg["game_id"],
                    "sport": leg["sport"],
                    "player": leg.get("player"),
                    "market": leg.get("market") or leg.get("market_key"),
                    "prediction": leg["prediction"],
                    "confidence": leg["confidence"],
                    "odds": float(leg.get("odds", -110)),
                    "commence_time": leg.get("commence_time"),
                }
            )

        return {
            "bet_type": "parlay",
            "legs": parlay_legs,
            "num_legs": len(legs),
            "combined_confidence": round(combined_prob, 4),
            "combined_decimal_odds": round(combined_decimal_odds, 4),
            "combined_american_odds": self._decimal_to_american(combined_decimal_odds),
        }

    def calculate_parlay_bet_size(
        self, parlay: Dict[str, Any], bankroll: Decimal
    ) -> Decimal:
        """Kelly-based sizing for parlays with extra conservatism."""
        decimal_odds = Decimal(str(parlay["combined_decimal_odds"]))
        prob = Decimal(str(parlay["combined_confidence"]))
        edge = prob * decimal_odds - 1
        if edge <= 0:
            return Decimal("0")
        kelly = edge / (decimal_odds - 1)
        bet_size = bankroll * kelly * self.KELLY_FRACTION
        max_bet = bankroll * self.MAX_BET_PERCENTAGE
        return min(bet_size, max_bet)

    @staticmethod
    def _american_to_decimal(odds: float) -> float:
        if odds > 0:
            return 1 + (odds / 100)
        return 1 + (100 / abs(odds))

    @staticmethod
    def _decimal_to_american(decimal_odds: float) -> int:
        if decimal_odds >= 2.0:
            return round((decimal_odds - 1) * 100)
        return round(-100 / (decimal_odds - 1))
