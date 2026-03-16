"""Benny V3 — Lean model with flat sizing and variance awareness.

Philosophy: trust the market more, trust AI confidence less.
- Stripped-down prompts (just data, no history/examples)
- Flat 2% bet sizing (no Kelly — AI confidence is unreliable)
- Odds-edge floor (AI must disagree with market by 5%+)
- Monte Carlo variance tracking
- Single fixed threshold (0.70 confidence, 5% EV)
"""
import json
from decimal import Decimal
from typing import Dict, Any

from benny.models.base import BennyModelBase
from benny.variance_tracker import VarianceTracker


class BennyV3(BennyModelBase):
    """Lean betting model — flat sizing, minimal prompts, variance-aware"""

    FLAT_BET_PCT = Decimal("0.02")  # 2% of bankroll
    MIN_CONFIDENCE = 0.70
    MIN_EV = 0.05
    MIN_EDGE_VS_MARKET = 0.05  # Must disagree with market by 5%+

    def __init__(self, table):
        self.table = table
        self.variance_tracker = VarianceTracker(table, self.pk)

    @property
    def pk(self) -> str:
        return "BENNY_V3"

    @property
    def version(self) -> str:
        return "v3"

    def build_game_prompt(self, game_data: Dict, context: Dict[str, Any]) -> str:
        home = game_data["home_team"]
        away = game_data["away_team"]

        # Build compact odds section
        odds_section = f"""MONEYLINE: Home {context['avg_h2h']['home']:+.0f} ({context['home_prob']:.1%}) | Away {context['avg_h2h']['away']:+.0f} ({context['away_prob']:.1%})"""
        if context.get("draw_prob"):
            odds_section += f" | Draw {context['avg_h2h'].get('draw', 0):+.0f} ({context['draw_prob']:.1%})"
        if context.get("avg_spread"):
            s = context["avg_spread"]
            odds_section += f"\nSPREAD: Home {s['home_point']:+.1f} ({s['home_price']:+.0f}) | Away {s['away_point']:+.1f} ({s['away_price']:+.0f})"
        if context.get("avg_total"):
            t = context["avg_total"]
            odds_section += f"\nTOTAL: O/U {t['point']:.1f} — Over {t['over_price']:+.0f} | Under {t['under_price']:+.0f}"

        return f"""Analyze this game and pick the best betting market. Be selective — only bet when you see a clear edge.

{away} @ {home} ({game_data['sport']}) — {game_data['commence_time']}

{odds_section}

ELO: {home} {context['home_elo']:.0f} | {away} {context['away_elo']:.0f} (diff: {context['home_elo'] - context['away_elo']:+.0f})

FORM (Last 5): {home} {context['home_form'].get('record', '?')} {context['home_form'].get('streak', '')} | {away} {context['away_form'].get('record', '?')} {context['away_form'].get('streak', '')}

INJURIES: {home}: {json.dumps(context['home_injuries']) if context['home_injuries'] else 'None'} | {away}: {json.dumps(context['away_injuries']) if context['away_injuries'] else 'None'}

H2H: {json.dumps(context['h2h_history']) if context['h2h_history'] else 'No history'}

RULES:
- Confidence must be your TRUE probability estimate (0.65-0.95 range)
- Only include markets where you're genuinely 70%+ confident
- EV = (confidence × payout) - 1 must be > 5%
- Skip entirely if edge is unclear

Respond with JSON only. Include only markets worth betting:
{{"h2h": {{"prediction": "Team (Moneyline)", "confidence": 0.75, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}, "spread": {{"prediction": "Team ±X (Spread)", "confidence": 0.72, "reasoning": "Brief", "key_factors": ["f1"]}}, "total": {{"prediction": "Over/Under X (Total)", "confidence": 0.70, "reasoning": "Brief", "key_factors": ["f1"]}}}}"""

    def build_prop_prompt(self, prop_data: Dict, player_stats: Dict, player_trends: Dict, matchup_data: Dict) -> str:
        over_odds = [o for o in prop_data["odds"] if o["side"] == "Over"]
        under_odds = [o for o in prop_data["odds"] if o["side"] == "Under"]
        avg_over = sum(o["price"] for o in over_odds) / len(over_odds) if over_odds else 0
        avg_under = sum(o["price"] for o in under_odds) / len(under_odds) if under_odds else 0

        return f"""Analyze this player prop. Only bet when stats clearly support it.

{prop_data['player']} ({prop_data['team']}) vs {prop_data['opponent']}
Market: {prop_data['market']} | Line: {prop_data['line']}
Odds: Over {avg_over:+.0f} | Under {avg_under:+.0f}

STATS (Last 20 games): {json.dumps(player_stats) if player_stats else 'No data'}
TRENDS (Last 10): {json.dumps(player_trends) if player_trends else 'No data'}
MATCHUP vs {prop_data['opponent']}: {json.dumps(matchup_data) if matchup_data else 'No data'}

RULES:
- Compare season avg and last 5 to the line
- Confidence must be your TRUE probability (0.65-0.95)
- Only bet when confidence ≥ 70% AND EV > 5%
- Skip if data is limited

JSON only:
{{"prediction": "Over/Under X.X (Market)", "confidence": 0.72, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}"""

    def calculate_bet_size(self, confidence: float, odds: float, bankroll: Decimal) -> Decimal:
        """Flat 2% of bankroll. No Kelly — AI confidence is unreliable."""
        return bankroll * self.FLAT_BET_PCT

    def get_threshold(self, sport: str, market: str) -> float:
        """Single fixed threshold. No adaptive nonsense."""
        return self.MIN_CONFIDENCE

    def should_bet(self, confidence: float, expected_value: float, implied_prob: float, sport: str, market: str) -> bool:
        """Bet only when: confidence ≥ 0.70, EV ≥ 5%, and AI disagrees with market by 5%+."""
        if confidence < self.MIN_CONFIDENCE:
            return False
        if expected_value < self.MIN_EV:
            return False
        # Edge vs market: AI confidence must exceed implied probability by 5%+
        edge_vs_market = confidence - implied_prob
        if edge_vs_market < self.MIN_EDGE_VS_MARKET:
            return False
        return True

    def post_run(self, results: Dict[str, Any]):
        """Run Monte Carlo variance simulation after each run."""
        try:
            sim = self.variance_tracker.run_simulation()
            if "error" not in sim:
                self.variance_tracker.save_simulation(sim)
                print(f"[V3] Variance: actual at {sim['actual_percentile']:.0%} percentile, "
                      f"{'within' if sim['is_within_expected'] else 'OUTSIDE'} expected range")
                print(f"[V3] Need {sim['bets_for_significance']} bets for statistical significance")
            else:
                print(f"[V3] Variance: {sim['error']} ({sim.get('bet_count', 0)} bets)")
        except Exception as e:
            print(f"[V3] Variance tracking error: {e}")
