"""Coaching Agent — generates a periodic LLM coaching memo from performance data."""

import json
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict

import boto3
from boto3.dynamodb.conditions import Key

bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")


class CoachingAgent:
    def __init__(self, table, pk="BENNY"):
        self.table = table
        self.pk = pk

    def generate_memo(self) -> str:
        """Gather all learning data, send to Claude, store memo. Returns memo text."""
        settled = self._get_settled_bets()
        features = self._get_feature_insights()
        calibration = self._get_calibration()
        variance = self._get_variance()
        cooldowns = self._get_cooldowns()

        # Check which cooldowns have expired → move to explore
        today = datetime.utcnow().date().isoformat()
        expired = [m for m, d in cooldowns.items() if d <= today]

        prompt = self._build_coach_prompt(settled, features, calibration, variance, cooldowns, expired)
        memo = self._call_llm(prompt)
        if memo:
            # Remove expired cooldowns so they get a fresh trial
            for m in expired:
                cooldowns.pop(m, None)
            # Parse new avoids from memo and add cooldowns
            new_avoids = self._parse_avoids(memo)
            for market in new_avoids:
                if market not in cooldowns:
                    cooldowns[market] = (datetime.utcnow().date() + timedelta(days=30)).isoformat()
            self._store_memo(memo, cooldowns)
        return memo

    def get_memo(self) -> str:
        """Read stored coaching memo from DynamoDB."""
        try:
            resp = self.table.get_item(
                Key={"pk": f"{self.pk}#LEARNING", "sk": "COACHING_MEMO"}
            )
            return resp.get("Item", {}).get("memo", "")
        except Exception:
            return ""

    def _get_settled_bets(self, days=30) -> list:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        try:
            resp = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk) & Key("sk").begins_with("BET#"),
                FilterExpression="settled_at > :cutoff AND #s IN (:w, :l)",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":cutoff": cutoff, ":w": "won", ":l": "lost"},
            )
            return resp.get("Items", [])
        except Exception:
            return []

    def _get_feature_insights(self) -> dict:
        try:
            resp = self.table.get_item(
                Key={"pk": f"{self.pk}#LEARNING", "sk": "FEATURES"}
            )
            return resp.get("Item", {}).get("insights", {})
        except Exception:
            return {}

    def _get_calibration(self) -> dict:
        try:
            resp = self.table.get_item(
                Key={"pk": f"{self.pk}#LEARNING", "sk": "CALIBRATION"}
            )
            return resp.get("Item", {}).get("calibration", {})
        except Exception:
            return {}

    def _get_variance(self) -> dict:
        try:
            resp = self.table.get_item(
                Key={"pk": f"{self.pk}#LEARNING", "sk": "VARIANCE"}
            )
            item = resp.get("Item", {})
            item.pop("pk", None)
            item.pop("sk", None)
            return item
        except Exception:
            return {}

    def _summarize_bets(self, bets: list) -> str:
        if not bets:
            return "No settled bets in last 30 days."

        wins = [b for b in bets if b.get("status") == "won"]
        total_wagered = sum(float(b.get("bet_amount", 0)) for b in bets)
        total_profit = sum(float(b.get("profit", 0)) for b in bets)
        roi = (total_profit / total_wagered * 100) if total_wagered > 0 else 0

        # By sport
        by_sport = {}
        for b in bets:
            s = b.get("sport", "?")
            by_sport.setdefault(s, {"w": 0, "t": 0})
            by_sport[s]["t"] += 1
            if b.get("status") == "won":
                by_sport[s]["w"] += 1

        # By market
        by_market = {}
        for b in bets:
            m = b.get("market_key", "?")
            by_market.setdefault(m, {"w": 0, "t": 0, "wagered": 0, "profit": 0})
            by_market[m]["t"] += 1
            by_market[m]["wagered"] += float(b.get("bet_amount", 0))
            by_market[m]["profit"] += float(b.get("profit", 0))
            if b.get("status") == "won":
                by_market[m]["w"] += 1

        # High-confidence losses
        high_conf_losses = [
            b for b in bets
            if b.get("status") == "lost" and float(b.get("confidence", 0)) > 0.80
        ]

        # Recent streak
        recent = sorted(bets, key=lambda b: b.get("sk", ""), reverse=True)[:10]
        streak = "".join("W" if b.get("status") == "won" else "L" for b in recent)

        lines = [
            f"OVERALL: {len(wins)}/{len(bets)} ({len(wins)/len(bets):.1%}), ROI: {roi:+.1f}%, Wagered: ${total_wagered:.0f}",
            f"LAST 10: {streak}",
            "",
            "BY SPORT:",
        ]
        for s, v in sorted(by_sport.items(), key=lambda x: x[1]["t"], reverse=True):
            wr = v["w"] / v["t"] if v["t"] else 0
            lines.append(f"  {s}: {v['w']}/{v['t']} ({wr:.1%})")

        lines.append("\nBY MARKET:")
        for m, v in sorted(by_market.items(), key=lambda x: x[1]["t"], reverse=True):
            wr = v["w"] / v["t"] if v["t"] else 0
            mr = (v["profit"] / v["wagered"] * 100) if v["wagered"] > 0 else 0
            lines.append(f"  {m}: {v['w']}/{v['t']} ({wr:.1%}), ROI: {mr:+.1f}%")

        if high_conf_losses:
            lines.append(f"\nHIGH-CONFIDENCE LOSSES (>80%): {len(high_conf_losses)}")
            for b in high_conf_losses[:5]:
                lines.append(
                    f"  {b.get('prediction', '?')} @ {float(b.get('confidence', 0)):.0%} "
                    f"— {b.get('ai_reasoning', 'no reasoning')[:80]}"
                )

        # Winning examples with reasoning
        recent_wins = [b for b in recent if b.get("status") == "won"][:3]
        if recent_wins:
            lines.append("\nRECENT WINS:")
            for b in recent_wins:
                lines.append(
                    f"  {b.get('prediction', '?')} @ {float(b.get('confidence', 0)):.0%} "
                    f"— {b.get('ai_reasoning', '')[:80]}"
                )

        # Factor analysis
        factor_perf = {}
        for b in bets:
            won = b.get("status") == "won"
            for f in b.get("ai_key_factors", []):
                factor_perf.setdefault(f, {"w": 0, "t": 0})
                factor_perf[f]["t"] += 1
                if won:
                    factor_perf[f]["w"] += 1
        good_factors = [(f, v) for f, v in factor_perf.items() if v["t"] >= 3 and v["w"] / v["t"] >= 0.60]
        bad_factors = [(f, v) for f, v in factor_perf.items() if v["t"] >= 3 and v["w"] / v["t"] <= 0.40]
        if good_factors or bad_factors:
            lines.append("\nFACTOR TRACK RECORD:")
            for f, v in sorted(good_factors, key=lambda x: x[1]["w"] / x[1]["t"], reverse=True)[:5]:
                lines.append(f"  ✓ {f}: {v['w']}/{v['t']} ({v['w']/v['t']:.0%})")
            for f, v in sorted(bad_factors, key=lambda x: x[1]["w"] / x[1]["t"])[:5]:
                lines.append(f"  ✗ {f}: {v['w']}/{v['t']} ({v['w']/v['t']:.0%})")

        return "\n".join(lines)

    def _format_features(self, features: dict) -> str:
        if not features:
            return "No feature analysis available."
        strongest = features.get("strongest_predictors", [])
        if not strongest:
            return "No strong predictors identified yet."
        lines = []
        for pred in strongest[:5]:
            f = pred.get("feature", "?")
            spread = float(pred.get("spread", 0))
            lines.append(f"{f}: {spread:.1%} win-rate spread")
            detail = features.get("insights", {}).get(f, {})
            for rng, data in sorted(detail.items(), key=lambda x: float(x[1].get("win_rate", 0)), reverse=True)[:3]:
                cnt = int(data.get("count", 0))
                if cnt >= 5:
                    lines.append(f"  {rng}: {float(data['win_rate']):.1%} ({cnt} bets)")
        return "\n".join(lines)

    def _format_calibration(self, cal: dict) -> str:
        if not cal:
            return "No calibration data."
        lines = []
        for bucket, data in sorted(cal.items()):
            if isinstance(data, dict) and data.get("count", 0) > 0:
                lines.append(
                    f"  {bucket}%: actual {float(data.get('actual_win_rate', 0)):.1%} "
                    f"(n={data['count']}, error={float(data.get('calibration_error', 0)):.1%})"
                )
        return "\n".join(lines) if lines else "No calibration data."

    def _build_coach_prompt(self, bets, features, calibration, variance, cooldowns, expired) -> str:
        bet_summary = self._summarize_bets(bets)
        feature_text = self._format_features(features)
        cal_text = self._format_calibration(calibration)

        variance_text = "No variance data."
        if variance and "actual_roi" in variance:
            variance_text = (
                f"ROI: {float(variance.get('actual_roi', 0)):.1%}, "
                f"Percentile: {float(variance.get('actual_percentile', 0)):.0%}, "
                f"Within expected: {variance.get('is_within_expected', '?')}, "
                f"Bets for significance: {variance.get('bets_for_significance', '?')}"
            )

        cooldown_text = "None."
        if cooldowns:
            active = {m: d for m, d in cooldowns.items() if m not in expired}
            parts = []
            if active:
                parts.append("ON COOLDOWN (do not re-add to AVOID):\n" + "\n".join(f"  {m} — revisit after {d}" for m, d in active.items()))
            if expired:
                parts.append("COOLDOWN EXPIRED (move to EXPLORE for 10-bet trial):\n" + "\n".join(f"  {m}" for m in expired))
            cooldown_text = "\n".join(parts)

        return f"""You are a sports betting coach. Benny reads this memo before every game analysis. Your job is to STEER bets toward higher-value opportunities, NOT to discourage betting.

CRITICAL: Benny MUST still place bets. Never recommend freezing, stopping, or skipping entire categories. Instead, recommend adjusting sizing or adding extra scrutiny.

PERFORMANCE DATA (Last 30 days):
{bet_summary}

FEATURE IMPORTANCE (which data points predict wins):
{feature_text}

CONFIDENCE CALIBRATION (stated confidence vs actual win rate):
{cal_text}

VARIANCE ANALYSIS:
{variance_text}

MARKET COOLDOWNS:
{cooldown_text}

Write a coaching memo (under 400 words) with these sections:
1. BET AGGRESSIVELY — specific sports/markets/situations where Benny has a proven edge. Be enthusiastic. Tell Benny to size up here.
2. BET CAUTIOUSLY — markets where results are mixed. Don't say "avoid" — say "reduce size" or "require extra factor confirmation."
3. CALIBRATION — note any overconfidence/underconfidence patterns. Never say "cap confidence" — instead say "when you feel X% confident, you're historically closer to Y%."
4. KEY RULES — 3-5 actionable rules. Frame positively (do this) not negatively (don't do that).
5. EXPLORE — markets with <20 bets and poor results OR markets whose cooldown just expired. Say "minimum bet size" not "freeze." Format: "EXPLORE: [market]"
6. AVOID — ONLY markets with 20+ bets and <35% win rate NOT already on cooldown. Format: "AVOID: [market]"

Markets "ON COOLDOWN" must NOT reappear in AVOID. "COOLDOWN EXPIRED" markets MUST appear in EXPLORE.

Tone: encouraging but honest. Benny should finish reading this and feel confident about where to bet, not afraid to bet."""

    def _get_cooldowns(self) -> dict:
        """Read persisted market cooldown dates from the coaching memo item."""
        try:
            resp = self.table.get_item(
                Key={"pk": f"{self.pk}#LEARNING", "sk": "COACHING_MEMO"}
            )
            return resp.get("Item", {}).get("cooldowns", {}) or {}
        except Exception:
            return {}

    def _parse_avoids(self, memo: str) -> list:
        """Extract market names from AVOID lines in the memo."""
        import re
        markets = []
        for line in memo.split("\n"):
            line = line.strip().lstrip("*-• ")
            if line.upper().startswith("AVOID:"):
                raw = line.split(":", 1)[1].strip().strip("*")
                # Take only the first word/underscore token (e.g. "soccer_epl")
                match = re.match(r'[\w]+', raw)
                if match:
                    markets.append(match.group())
        return markets

    def _call_llm(self, prompt: str) -> str:
        try:
            resp = bedrock.invoke_model(
                modelId="us.anthropic.claude-sonnet-4-5-20250929-v1:0",
                body=json.dumps({
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 900,
                    "messages": [{"role": "user", "content": prompt}],
                }),
            )
            result = json.loads(resp["body"].read())
            return result["content"][0]["text"]
        except Exception as e:
            print(f"[COACH] LLM error: {e}")
            return ""

    def _store_memo(self, memo: str, cooldowns: dict = None):
        item = {
            "pk": f"{self.pk}#LEARNING",
            "sk": "COACHING_MEMO",
            "memo": memo,
            "updated_at": datetime.utcnow().isoformat(),
        }
        if cooldowns:
            item["cooldowns"] = cooldowns
        self.table.put_item(Item=item)
        print(f"[COACH] Stored coaching memo ({len(memo)} chars), cooldowns: {cooldowns or {}}")
