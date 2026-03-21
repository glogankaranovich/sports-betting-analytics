"""Benny V3 — Lean model with flat sizing and variance awareness.

Philosophy: trust the market more, trust AI confidence less.
- Stripped-down prompts (just data, no history/examples)
- Flat 5% bet sizing (no Kelly — AI confidence is unreliable)
- Sport-specific edge floors (NBA 10%, less liquid markets 6-8%)
- ROI-based auto-gating: learns from settled bets, auto-blocks bleeding markets
- Confidence calibration: maps raw AI confidence to actual win rates
- Monte Carlo variance tracking
"""
import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, Any

from boto3.dynamodb.conditions import Key

from benny.models.base import BennyModelBase
from benny.variance_tracker import VarianceTracker


class BennyV3(BennyModelBase):
    """Lean betting model — flat sizing, minimal prompts, variance-aware"""

    FLAT_BET_PCT = Decimal("0.05")  # 5% of bankroll
    MIN_CONFIDENCE = 0.70
    MIN_EV = 0.05
    DEFAULT_EDGE_FLOOR = 0.08  # Default: 8% edge vs market

    # Sport-specific edge floors — efficient markets need higher edge
    SPORT_EDGE_FLOORS = {
        "basketball_nba": 0.10,
        "americanfootball_nfl": 0.10,
        "basketball_wnba": 0.08,
        "americanfootball_ncaaf": 0.07,
        "basketball_ncaab": 0.06,
        "basketball_wncaab": 0.06,
        "soccer_epl": 0.08,
        "soccer_usa_mls": 0.06,
        "baseball_mlb": 0.08,
        "icehockey_nhl": 0.08,
    }

    # ROI gating thresholds
    ROI_MIN_SAMPLE = 15
    ROI_BLOCK_THRESHOLD = -0.15  # Block at -15% ROI
    ROI_PROBATION_THRESHOLD = -0.05  # Probation at -5% ROI

    def __init__(self, table):
        self.table = table
        self.variance_tracker = VarianceTracker(table, self.pk)
        self._roi_cache = None
        self._calibration_cache = None

    def get_min_bet(self) -> Decimal:
        return Decimal("5.00")

    @property
    def pk(self) -> str:
        return "BENNY_V3"

    @property
    def version(self) -> str:
        return "v3"

    _coaching_memo_cache = None

    def _get_coaching_memo(self) -> str:
        if self._coaching_memo_cache is not None:
            return self._coaching_memo_cache
        try:
            from benny.coaching_agent import CoachingAgent

            self._coaching_memo_cache = CoachingAgent(self.table, self.pk).get_memo()
        except Exception:
            self._coaching_memo_cache = ""
        return self._coaching_memo_cache

    def build_game_prompt(self, game_data: Dict, context: Dict[str, Any]) -> str:
        home = game_data["home_team"]
        away = game_data["away_team"]
        coaching_memo = self._get_coaching_memo()

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

        memo_block = f"\nCOACHING MEMO:\n{coaching_memo}\n" if coaching_memo else ""
        cal_block = self._get_calibration_text()
        cal_section = f"\n{cal_block}\n" if cal_block else ""

        return f"""Analyze this game and pick the best betting market. Be selective — only bet when you see a clear edge.

{away} @ {home} ({game_data['sport']}) — {game_data['commence_time']}

{odds_section}

ELO: {home} {context['home_elo']:.0f} | {away} {context['away_elo']:.0f} (diff: {context['home_elo'] - context['away_elo']:+.0f})

FORM (Last 5): {home} {context['home_form'].get('record', '?')} {context['home_form'].get('streak', '')} | {away} {context['away_form'].get('record', '?')} {context['away_form'].get('streak', '')}

INJURIES: {home}: {json.dumps(context['home_injuries']) if context['home_injuries'] else 'None'} | {away}: {json.dumps(context['away_injuries']) if context['away_injuries'] else 'None'}

H2H: {json.dumps(context['h2h_history']) if context['h2h_history'] else 'No history'}
{memo_block}{cal_section}
RULES:
- Confidence must be your TRUE probability estimate (0.65-0.95 range)
- If calibration data is shown above, adjust: when you said X% before, you actually won Y%
- Only include markets where you're genuinely 70%+ confident
- EV = (confidence × payout) - 1 must be > 5%
- Follow coaching memo rules if present
- Skip entirely if edge is unclear

Respond with JSON only. Include only markets worth betting:
{{"h2h": {{"prediction": "Team (Moneyline)", "confidence": 0.75, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}, "spread": {{"prediction": "Team ±X (Spread)", "confidence": 0.72, "reasoning": "Brief", "key_factors": ["f1"]}}, "total": {{"prediction": "Over/Under X (Total)", "confidence": 0.70, "reasoning": "Brief", "key_factors": ["f1"]}}}}"""

    def build_prop_prompt(
        self,
        prop_data: Dict,
        player_stats: Dict,
        player_trends: Dict,
        matchup_data: Dict,
    ) -> str:
        over_odds = [o for o in prop_data["odds"] if o["side"] == "Over"]
        under_odds = [o for o in prop_data["odds"] if o["side"] == "Under"]
        avg_over = (
            sum(o["price"] for o in over_odds) / len(over_odds) if over_odds else 0
        )
        avg_under = (
            sum(o["price"] for o in under_odds) / len(under_odds) if under_odds else 0
        )
        coaching_memo = self._get_coaching_memo()
        memo_block = f"\nCOACHING MEMO:\n{coaching_memo}\n" if coaching_memo else ""
        cal_block = self._get_calibration_text()
        cal_section = f"\n{cal_block}\n" if cal_block else ""

        return f"""Analyze this player prop. Only bet when stats clearly support it.

{prop_data['player']} ({prop_data['team']}) vs {prop_data['opponent']}
Market: {prop_data['market']} | Line: {prop_data['line']}
Odds: Over {avg_over:+.0f} | Under {avg_under:+.0f}

STATS (Last 20 games): {json.dumps(player_stats, default=str) if player_stats else 'No data'}
TRENDS (Last 10): {json.dumps(player_trends, default=str) if player_trends else 'No data'}
MATCHUP vs {prop_data['opponent']}: {json.dumps(matchup_data, default=str) if matchup_data else 'No data'}
{memo_block}{cal_section}
RULES:
- Compare season avg and last 5 to the line
- Confidence must be your TRUE probability (0.65-0.95)
- If calibration data is shown above, adjust: when you said X% before, you actually won Y%
- Only bet when confidence ≥ 70% AND EV > 5%
- Follow coaching memo rules if present
- Skip if data is limited

JSON only:
{{"prediction": "Over/Under X.X (Market)", "confidence": 0.72, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}"""

    def calculate_bet_size(
        self, confidence: float, odds: float, bankroll: Decimal
    ) -> Decimal:
        """Flat 5% of bankroll. No Kelly — AI confidence is unreliable."""
        return bankroll * self.FLAT_BET_PCT

    def get_threshold(self, sport: str, market: str) -> float:
        """Single fixed threshold. No adaptive nonsense."""
        return self.MIN_CONFIDENCE

    def should_bet(
        self,
        confidence: float,
        expected_value: float,
        implied_prob: float,
        sport: str,
        market: str,
    ) -> bool:
        """Gate bets through: confidence, EV, sport-specific edge floor, ROI auto-gating, and calibration."""
        if confidence < self.MIN_CONFIDENCE:
            return False
        if expected_value < self.MIN_EV:
            return False

        # Sport-specific edge floor
        edge_floor = self.SPORT_EDGE_FLOORS.get(sport, self.DEFAULT_EDGE_FLOOR)
        edge_vs_market = confidence - implied_prob
        if edge_vs_market < edge_floor:
            return False

        # ROI auto-gating: learn from settled bets, block bleeding sport+market combos
        roi_data = self._get_roi_data()
        key = f"{sport}|{market}"
        if key in roi_data and roi_data[key]["total"] >= self.ROI_MIN_SAMPLE:
            roi = roi_data[key]["roi"]
            if roi <= self.ROI_BLOCK_THRESHOLD:
                print(
                    f"  [V3-GATE] BLOCKED {key}: ROI={roi:.1%} after {roi_data[key]['total']} bets"
                )
                return False
            if roi <= self.ROI_PROBATION_THRESHOLD:
                # Probation: require extra 5% edge on top of sport floor
                if edge_vs_market < edge_floor + 0.05:
                    print(
                        f"  [V3-GATE] PROBATION {key}: ROI={roi:.1%}, edge {edge_vs_market:.1%} < {edge_floor + 0.05:.1%}"
                    )
                    return False

        # Calibration check: use actual win rate at this confidence level
        calibrated = self._calibrate_confidence(confidence)
        if calibrated < implied_prob:
            print(
                f"  [V3-CAL] Rejected: raw={confidence:.0%} calibrates to {calibrated:.0%}, market={implied_prob:.0%}"
            )
            return False

        return True

    def _get_roi_data(self) -> Dict[str, Any]:
        """Load ROI by sport|market from settled bets. Cached per run."""
        if self._roi_cache is not None:
            return self._roi_cache

        self._roi_cache = {}
        try:
            cutoff = (datetime.utcnow() - timedelta(days=60)).isoformat()
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                FilterExpression="settled_at > :cutoff AND #s IN (:w, :l)",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={
                    ":cutoff": cutoff,
                    ":w": "won",
                    ":l": "lost",
                },
            )
            for b in response.get("Items", []):
                key = f"{b.get('sport', '?')}|{b.get('market_key', '?')}"
                if key not in self._roi_cache:
                    self._roi_cache[key] = {"total": 0, "wagered": 0.0, "profit": 0.0}
                self._roi_cache[key]["total"] += 1
                self._roi_cache[key]["wagered"] += float(b.get("bet_amount", 0))
                self._roi_cache[key]["profit"] += float(b.get("profit", 0))

            for key, data in self._roi_cache.items():
                data["roi"] = (
                    data["profit"] / data["wagered"] if data["wagered"] > 0 else 0
                )
        except Exception as e:
            print(f"[V3] ROI cache error: {e}")
        return self._roi_cache

    def _calibrate_confidence(self, raw_confidence: float) -> float:
        """Map raw AI confidence to historical win rate at that bucket."""
        if self._calibration_cache is None:
            self._calibration_cache = self._build_calibration_table()
        bucket = round(raw_confidence, 1)
        return self._calibration_cache.get(bucket, raw_confidence)

    def _build_calibration_table(self) -> dict:
        """Build confidence → actual win rate from settled bets."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                FilterExpression="#s IN (:w, :l)",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":w": "won", ":l": "lost"},
                ProjectionExpression="confidence, #s",
            )
            buckets = {}
            for b in response.get("Items", []):
                conf = round(float(b.get("confidence", 0)), 1)
                won = b.get("status") == "won"
                if conf not in buckets:
                    buckets[conf] = {"wins": 0, "total": 0}
                buckets[conf]["total"] += 1
                if won:
                    buckets[conf]["wins"] += 1

            table = {}
            for conf, data in buckets.items():
                if data["total"] >= 8:
                    table[conf] = data["wins"] / data["total"]
            if table:
                print(f"[V3] Calibration: {table}")
            return table
        except Exception as e:
            print(f"[V3] Calibration error: {e}")
            return {}

    def _get_calibration_text(self) -> str:
        """Format calibration table for inclusion in prompts."""
        if self._calibration_cache is None:
            self._calibration_cache = self._build_calibration_table()
        if not self._calibration_cache:
            return ""
        lines = ["YOUR CALIBRATION (stated confidence → actual win rate):"]
        for conf in sorted(self._calibration_cache.keys()):
            actual = self._calibration_cache[conf]
            diff = actual - conf
            label = (
                "overconfident"
                if diff < -0.05
                else "underconfident"
                if diff > 0.05
                else "calibrated"
            )
            lines.append(f"  {conf:.0%} → {actual:.0%} ({label})")
        return "\n".join(lines)

    def post_run(self, results: Dict[str, Any]):
        """Run Monte Carlo variance simulation and log ROI gating status."""
        try:
            sim = self.variance_tracker.run_simulation()
            if "error" not in sim:
                self.variance_tracker.save_simulation(sim)
                print(
                    f"[V3] Variance: actual at {sim['actual_percentile']:.0%} percentile, "
                    f"{'within' if sim['is_within_expected'] else 'OUTSIDE'} expected range"
                )
                print(
                    f"[V3] Need {sim['bets_for_significance']} bets for statistical significance"
                )
            else:
                print(f"[V3] Variance: {sim['error']} ({sim.get('bet_count', 0)} bets)")
        except Exception as e:
            print(f"[V3] Variance tracking error: {e}")

        # Log ROI gating status
        roi_data = self._get_roi_data()
        if roi_data:
            print("[V3] ROI gating status:")
            for key in sorted(roi_data.keys()):
                d = roi_data[key]
                status = (
                    "BLOCKED"
                    if d["roi"] <= self.ROI_BLOCK_THRESHOLD
                    and d["total"] >= self.ROI_MIN_SAMPLE
                    else "PROBATION"
                    if d["roi"] <= self.ROI_PROBATION_THRESHOLD
                    and d["total"] >= self.ROI_MIN_SAMPLE
                    else "OK"
                )
                print(f"  {key}: {d['total']} bets, ROI={d['roi']:.1%} [{status}]")
