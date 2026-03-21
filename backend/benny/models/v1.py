"""Benny V1 — Original model with Kelly sizing and adaptive thresholds.

- Full prompts with perf history, what_works/fails, mistakes, winning examples/factors
- Kelly criterion bet sizing via BankrollManager
- Adaptive confidence thresholds via LearningEngine
- Post-run: update_learning_parameters

TODO: Consider adding feature analysis (OutcomeAnalyzer + FeatureExtractor) to post_run.
  V2 tried this but the loop was broken (OutcomeAnalyzer filtered for status='settled' instead
  of 'won'/'lost' — now fixed). The idea: extract structured features per bet (elo_diff,
  fatigue, injury_advantage, form_advantage, etc.), analyze which correlate with wins, and
  use insights for your own analysis. Don't inject into the AI prompt — it didn't help V2.
  Would need: FeatureExtractor.extract_features() in analyze_games, store with bet,
  then OutcomeAnalyzer.analyze_features() + save_insights() in post_run.
"""
import json
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict

from boto3.dynamodb.conditions import Key

from benny.models.base import BennyModelBase


class BennyV1(BennyModelBase):
    BASE_MIN_CONFIDENCE = 0.70
    MIN_EV = 0.05
    DEFAULT_EDGE_FLOOR = 0.08
    MAX_BET_PERCENTAGE = 0.20
    MIN_SAMPLE_SIZE = 30
    WEEKLY_BUDGET = Decimal("100.00")

    # Sport-specific edge floors — same as V3
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

    def __init__(self, table, learning_engine, bankroll_manager):
        self.table = table
        self.learning_engine = learning_engine
        self.bankroll_manager = bankroll_manager

    @property
    def pk(self) -> str:
        return "BENNY"

    @property
    def version(self) -> str:
        return "v1"

    # --- Prompt helpers ---

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

    def _get_what_works_analysis(self) -> str:
        params = self.learning_engine.params
        insights = []
        for src in ("performance_by_sport", "performance_by_market"):
            for key, stats in params.get(src, {}).items():
                if stats["total"] >= 5 and stats["wins"] / stats["total"] > 0.55:
                    wr = stats["wins"] / stats["total"]
                    insights.append(
                        f"✓ {key}: {wr:.1%} win rate ({stats['wins']}/{stats['total']})"
                    )
        return (
            "\n".join(insights)
            if insights
            else "Not enough data yet (need 5+ bets per category)"
        )

    def _get_what_fails_analysis(self) -> str:
        params = self.learning_engine.params
        warnings = []
        for src in ("performance_by_sport", "performance_by_market"):
            for key, stats in params.get(src, {}).items():
                if stats["total"] >= 5 and stats["wins"] / stats["total"] < 0.45:
                    wr = stats["wins"] / stats["total"]
                    warnings.append(
                        f"✗ {key}: {wr:.1%} win rate ({stats['wins']}/{stats['total']}) - be very selective, require higher confidence"
                    )
        return "\n".join(warnings) if warnings else "No clear failure patterns yet"

    def _analyze_recent_mistakes(self, limit: int = 10) -> str:
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                ScanIndexForward=False,
                Limit=200,
            )
            losses = [
                b for b in response.get("Items", []) if b.get("status") == "lost"
            ][:limit]
            if not losses:
                return "No recent losses to analyze"

            patterns = []
            high_conf = [b for b in losses if float(b.get("confidence", 0)) > 0.75]
            if len(high_conf) > len(losses) * 0.5:
                patterns.append(
                    f"⚠️ {len(high_conf)}/{len(losses)} losses were high confidence (>75%) - may be overconfident"
                )
            underdogs = [b for b in losses if float(b.get("odds", 0)) > 0]
            if len(underdogs) > len(losses) * 0.6:
                patterns.append(
                    f"⚠️ {len(underdogs)}/{len(losses)} losses were underdogs (+odds) - may be chasing value"
                )
            sport_losses = {}
            for bet in losses:
                s = bet.get("sport", "unknown")
                sport_losses[s] = sport_losses.get(s, 0) + 1
            for sport, count in sport_losses.items():
                if count >= 3:
                    patterns.append(f"⚠️ {count} recent losses in {sport}")
            return (
                "\n".join(patterns)
                if patterns
                else "No clear patterns in recent losses"
            )
        except Exception as e:
            return "Error analyzing recent mistakes"

    def _get_winning_examples(self, sport: str, limit: int = 3) -> str:
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                ScanIndexForward=False,
                Limit=200,
            )
            wins = [
                b
                for b in response.get("Items", [])
                if b.get("status") == "won" and b.get("sport") == sport
            ][:limit]
            if not wins:
                return f"No winning bets yet for {sport}"
            examples = []
            for bet in wins:
                profit = float(bet.get("profit", 0))
                confidence = float(bet.get("confidence", 0))
                reasoning = bet.get("ai_reasoning", "N/A")[:100]
                examples.append(
                    f"✓ {bet.get('prediction')} ({confidence:.0%} conf) - Won ${profit:.2f}\n  Reasoning: {reasoning}"
                )
            return "\n\n".join(examples)
        except Exception as e:
            return f"Error loading winning examples for {sport}"

    def _extract_winning_factors(self) -> str:
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                FilterExpression="#status IN (:won, :lost)",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":won": "won", ":lost": "lost"},
                Limit=100,
            )
            bets = response.get("Items", [])
            if len(bets) < 10:
                return "Not enough settled bets to analyze factors (need 10+)"
            factor_perf = {}
            for bet in bets:
                won = bet.get("status") == "won"
                for factor in bet.get("ai_key_factors", []):
                    if factor not in factor_perf:
                        factor_perf[factor] = {"wins": 0, "total": 0}
                    factor_perf[factor]["total"] += 1
                    if won:
                        factor_perf[factor]["wins"] += 1
            insights = []
            for factor, stats in sorted(
                factor_perf.items(),
                key=lambda x: x[1]["wins"] / max(x[1]["total"], 1),
                reverse=True,
            ):
                if stats["total"] >= 3:
                    wr = stats["wins"] / stats["total"]
                    if wr >= 0.60:
                        insights.append(
                            f"✓ {factor}: {wr:.0%} ({stats['wins']}/{stats['total']})"
                        )
                    elif wr <= 0.40:
                        insights.append(
                            f"✗ {factor}: {wr:.0%} ({stats['wins']}/{stats['total']})"
                        )
            return (
                "\n".join(insights)
                if insights
                else "No clear factor patterns yet (need factors with 3+ occurrences)"
            )
        except Exception as e:
            return "Error analyzing winning factors"

    def _get_model_benchmarks(self, sport: str) -> str:
        try:
            from constants import SYSTEM_MODELS

            benchmarks = []
            for model in SYSTEM_MODELS:
                response = self.table.query(
                    IndexName="VerifiedAnalysisGSI",
                    KeyConditionExpression=Key("verified_analysis_pk").eq(
                        f"VERIFIED#{model}#{sport}#game"
                    ),
                    ScanIndexForward=False,
                    Limit=50,
                )
                preds = response.get("Items", [])
                if len(preds) >= 10:
                    correct = sum(1 for p in preds if p.get("analysis_correct"))
                    accuracy = correct / len(preds)
                    benchmarks.append(
                        f"{model}: {accuracy:.1%} ({correct}/{len(preds)})"
                    )
            return (
                "\n".join(benchmarks)
                if benchmarks
                else f"No benchmark data for {sport}"
            )
        except Exception as e:
            return f"Error loading benchmarks for {sport}"

    def _get_prop_market_performance(self, market_key: str) -> str:
        perf = self.learning_engine.params.get("performance_by_prop_market", {})
        stats = perf.get(market_key, {})
        if not stats or stats.get("total", 0) < 3:
            return f"Not enough data for {market_key} (need 3+ bets)"
        wr = stats["wins"] / stats["total"]
        return f"{market_key}: {stats['wins']}/{stats['total']} ({wr:.1%} win rate)"

    # --- Interface methods ---

    def _build_perf_context(self, perf_stats: Dict) -> str:
        if "overall" not in perf_stats:
            return ""
        return f"""
BENNY'S HISTORICAL PERFORMANCE (Last 30 days):
Overall: {perf_stats['overall']['win_rate']} win rate, {perf_stats['overall']['roi']} ROI ({perf_stats['overall']['total_bets']} bets)
By Sport: {', '.join(f"{s}: {r}" for s, r in perf_stats['by_sport'].items())}
By Market: {', '.join(f"{m}: {r}" for m, r in perf_stats['by_market'].items())}
Note: Use this to inform confidence - be more conservative in markets where you've struggled."""

    def build_game_prompt(self, game_data: Dict, context: Dict[str, Any]) -> str:
        sport = game_data["sport"]
        params = self.learning_engine.params
        bankroll = context["bankroll"]
        coaching_memo = self._get_coaching_memo()
        perf_warnings = self.learning_engine.get_performance_warnings(sport)
        cal_text = self._get_calibration_text()
        cal_section = f"\n{cal_text}\n" if cal_text else ""

        return f"""You are Benny, an expert sports betting analyst. Your goal is to achieve 15%+ ROI through strategic betting decisions.

RISK PARAMETERS:
- Kelly Fraction: {params.get('kelly_fraction', 0.5)} (bet sizing multiplier)
- Max Bet Size: {self.MAX_BET_PERCENTAGE*100:.0f}% of bankroll (${float(bankroll * Decimal(str(self.MAX_BET_PERCENTAGE))):.2f})
- Target ROI: {params.get('target_roi', 0.15)*100:.0f}%
- Current Bankroll: ${float(bankroll):.2f}

{perf_warnings}

COACHING MEMO (from your performance coach — follow these rules):
{coaching_memo if coaching_memo else 'No coaching data yet — use your best judgment.'}
{cal_section}

Game: {game_data['away_team']} @ {game_data['home_team']}
Sport: {game_data['sport']}
Time: {game_data['commence_time']}

MARKET ODDS:
{context['market_odds']}

ELO RATINGS (Team Strength):
Home: {context['home_elo']:.0f} | Away: {context['away_elo']:.0f} | Difference: {context['home_elo'] - context['away_elo']:+.0f}
Note: Higher = stronger. Difference >50 = significant edge. Average team = 1500.

OPPONENT-ADJUSTED EFFICIENCY:
Home: {json.dumps(context.get('home_adjusted'), indent=2) if context.get('home_adjusted') else 'No data'}
Away: {json.dumps(context.get('away_adjusted'), indent=2) if context.get('away_adjusted') else 'No data'}

TRAVEL & FATIGUE:
{json.dumps(context.get('fatigue'), indent=2) if context.get('fatigue') else 'No data'}

WEATHER CONDITIONS:
{json.dumps(context.get('weather'), indent=2) if context.get('weather') else 'Indoor venue or no data'}

RECENT FORM (Last 5 games):
Home: {context['home_form'].get('record', 'Unknown')} - {context['home_form'].get('streak', '')}
Away: {context['away_form'].get('record', 'Unknown')} - {context['away_form'].get('streak', '')}

HEAD-TO-HEAD (Last 3 meetings):
{json.dumps(context.get('h2h_history'), indent=2) if context.get('h2h_history') else 'No history'}

KEY INJURIES:
Home: {json.dumps(context.get('home_injuries'), indent=2) if context.get('home_injuries') else 'None'}
Away: {json.dumps(context.get('away_injuries'), indent=2) if context.get('away_injuries') else 'None'}

NEWS SENTIMENT (Last 48 hours):
Home: Sentiment={context.get('home_news', {}).get('sentiment_score', 0):.2f}, Impact={context.get('home_news', {}).get('impact_score', 0):.1f}, Articles={context.get('home_news', {}).get('news_count', 0)}
Away: Sentiment={context.get('away_news', {}).get('sentiment_score', 0):.2f}, Impact={context.get('away_news', {}).get('impact_score', 0):.1f}, Articles={context.get('away_news', {}).get('news_count', 0)}

RAW TEAM STATS (Season Averages):
Home: {json.dumps(context.get('home_stats'), indent=2) if context.get('home_stats') else 'No data'}
Away: {json.dumps(context.get('away_stats'), indent=2) if context.get('away_stats') else 'No data'}

ANALYSIS INSTRUCTIONS:
1. Analyze ALL available markets (moneyline, spread, total)
2. Prioritize Elo ratings and opponent-adjusted metrics
3. Factor in fatigue if either team has score >50 or traveled >1000 miles
4. Consider weather impact if marked as "high" or "moderate"
5. FOLLOW YOUR COACHING MEMO — avoid markets/situations it flags
6. If calibration data is shown above, adjust: when you said X% before, you actually won Y%
7. CRITICAL BETTING THRESHOLDS:
   - Minimum Confidence: {self.BASE_MIN_CONFIDENCE} (65%) - Do not bet below this
   - Minimum Expected Value/ROI: {self.MIN_EV} (5%) - Only bet when expected ROI > 5%
   - Calculate EV/Expected ROI = (confidence × payout) - 1
   - NEVER bet on negative expected ROI - you will lose money over time
8. Be highly selective - quality over quantity. Skip games where edge is unclear.

Respond with JSON only - include ALL markets you want to bet on:
{{"h2h": {{"prediction": "Team Name (Moneyline)", "confidence": 0.75, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}, "spread": {{"prediction": "Team Name -X.X (Spread)", "confidence": 0.70, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}, "total": {{"prediction": "Over/Under XXX.X (Total)", "confidence": 0.65, "reasoning": "Brief", "key_factors": ["f1", "f2"]}}}}

IMPORTANT: 
- Include market type in prediction text for clarity
- Only include markets where confidence >= {self.BASE_MIN_CONFIDENCE} AND expected ROI >= {self.MIN_EV}
- Expected ROI = (confidence × payout) - 1 must be positive and > 5%
- When in doubt, skip the bet - protecting bankroll is priority #1"""

    def build_prop_prompt(
        self,
        prop_data: Dict,
        player_stats: Dict,
        player_trends: Dict,
        matchup_data: Dict,
    ) -> str:
        params = self.learning_engine.params
        bankroll = self.bankroll_manager.bankroll

        # Calculate avg odds
        over_odds = [o for o in prop_data["odds"] if o["side"] == "Over"]
        under_odds = [o for o in prop_data["odds"] if o["side"] == "Under"]
        avg_over = (
            sum(o["price"] for o in over_odds) / len(over_odds) if over_odds else 0
        )
        avg_under = (
            sum(o["price"] for o in under_odds) / len(under_odds) if under_odds else 0
        )

        def _american_to_probability(odds):
            if odds > 0:
                return 100 / (odds + 100)
            return abs(odds) / (abs(odds) + 100)

        over_prob = _american_to_probability(avg_over) if avg_over else 0.5
        under_prob = _american_to_probability(avg_under) if avg_under else 0.5

        coaching_memo = self._get_coaching_memo()
        cal_text = self._get_calibration_text()
        cal_section = f"\n{cal_text}\n" if cal_text else ""

        return f"""You are Benny, an expert sports betting analyst. Your goal is to achieve 15%+ ROI through strategic betting decisions.

RISK PARAMETERS:
- Kelly Fraction: {params.get('kelly_fraction', 0.5)} (bet sizing multiplier)
- Max Bet Size: {self.MAX_BET_PERCENTAGE*100:.0f}% of bankroll (${float(bankroll * Decimal(str(self.MAX_BET_PERCENTAGE))):.2f})
- Current Bankroll: ${float(bankroll):.2f}

COACHING MEMO (from your performance coach — follow these rules):
{coaching_memo if coaching_memo else 'No coaching data yet — use your best judgment.'}
{cal_section}

Player: {prop_data['player']} ({prop_data['team']})
Opponent: {prop_data['opponent']}
Market: {prop_data['market']}
Line: {prop_data['line']}
Sport: {prop_data['sport']}

MARKET ODDS:
Over {prop_data['line']}: {avg_over} ({over_prob:.1%} implied)
Under {prop_data['line']}: {avg_under} ({under_prob:.1%} implied)

PLAYER SEASON STATS (Last 20 games):
{json.dumps(player_stats, indent=2, default=str) if player_stats else 'No season data available'}

RECENT TRENDS (Last 10 games for this market):
{json.dumps(player_trends, indent=2, default=str) if player_trends else 'No trend data available'}

MATCHUP HISTORY vs {prop_data['opponent']}:
{json.dumps(matchup_data, indent=2, default=str) if matchup_data else 'No matchup history available'}

ANALYSIS INSTRUCTIONS:
1. Compare player's season average and last 5 games to the line
2. Consider recent trends - is player hot or cold?
3. Factor in matchup history against this opponent
4. FOLLOW YOUR COACHING MEMO — avoid markets/situations it flags
5. If calibration data is shown above, adjust: when you said X% before, you actually won Y%
6. CRITICAL BETTING THRESHOLDS:
   - Minimum Confidence: {self.BASE_MIN_CONFIDENCE} (65%) - Do not bet below this
   - Minimum Expected Value/ROI: {self.MIN_EV} (5%) - Only bet when expected ROI > 5%
   - Calculate EV/Expected ROI = (confidence × payout) - 1
   - NEVER bet on negative expected ROI - you will lose money over time
7. Be highly selective - props are harder to predict than games
8. Skip if player data is limited or matchup is unclear

Respond with JSON only:
{{"prediction": "Over/Under X.X (Player Market)", "confidence": 0.70, "reasoning": "Brief explanation", "key_factors": ["factor1", "factor2"]}}

IMPORTANT: 
- Include market type in prediction for clarity (e.g., "Over 25.5 (Points)", "Under 8.5 (Rebounds)")
- Only bet when confidence >= {self.BASE_MIN_CONFIDENCE} AND expected ROI >= {self.MIN_EV}
- Expected ROI = (confidence × payout) - 1 must be positive and > 5%
- When in doubt, skip - protecting bankroll is priority #1"""

    def _get_perf_stats(self) -> Dict:
        """Lightweight perf stats for prop prompt (game prompt gets it via context)."""
        # This will be called from build_prop_prompt. The trader passes perf_stats
        # in context for game prompts, but prop prompts need it too.
        try:
            from datetime import timedelta

            cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                FilterExpression="settled_at > :cutoff AND #status IN (:won, :lost)",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":cutoff": cutoff,
                    ":won": "won",
                    ":lost": "lost",
                },
            )
            bets = response.get("Items", [])
            if not bets:
                return {}
            wins = sum(1 for b in bets if b.get("status") == "won")
            total_wagered = sum(float(b.get("bet_amount", 0)) for b in bets)
            total_profit = sum(float(b.get("profit", 0)) for b in bets)
            roi = (total_profit / total_wagered * 100) if total_wagered > 0 else 0
            by_sport, by_market = {}, {}
            for b in bets:
                s, m = b.get("sport", "?"), b.get("market_key", "?")
                for d, k in ((by_sport, s), (by_market, m)):
                    if k not in d:
                        d[k] = {"w": 0, "t": 0}
                    d[k]["t"] += 1
                    if b.get("status") == "won":
                        d[k]["w"] += 1
            return {
                "overall": {
                    "win_rate": f"{wins}/{len(bets)} ({wins/len(bets):.1%})",
                    "roi": f"{roi:.1f}%",
                    "total_bets": len(bets),
                },
                "by_sport": {s: f"{v['w']}/{v['t']}" for s, v in by_sport.items()},
                "by_market": {m: f"{v['w']}/{v['t']}" for m, v in by_market.items()},
            }
        except Exception:
            return {}

    def _get_feature_insights(self) -> str:
        """V1 has no feature insights."""
        return "No learned insights available (v1)"

    def _get_calibration_text(self) -> str:
        """Format calibration table for inclusion in prompts."""
        if not hasattr(self, "_calibration_cache"):
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

    def calculate_bet_size(
        self, confidence: float, odds: float, bankroll: Decimal
    ) -> Decimal:
        calibrated = self._calibrate_confidence(confidence)
        size = self.bankroll_manager.calculate_bet_size(calibrated, odds)
        return max(size, self.get_min_bet()) if size > Decimal("0") else size

    def _calibrate_confidence(self, raw_confidence: float) -> float:
        """Map raw AI confidence to historical win rate at that level."""
        if not hasattr(self, "_calibration_cache"):
            self._calibration_cache = self._build_calibration_table()
        bucket = round(raw_confidence, 1)
        # If no calibration data, use raw confidence (don't penalize)
        return self._calibration_cache.get(bucket, raw_confidence)

    def _build_calibration_table(self) -> dict:
        """Build confidence → actual win rate mapping from settled bets."""
        try:
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq("BENNY")
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
                if data["total"] >= 10:  # need enough data
                    table[conf] = data["wins"] / data["total"]
            if table:
                print(f"Calibration table: {table}")
            return table
        except Exception as e:
            print(f"Failed to build calibration table: {e}")
            return {}

    def get_threshold(self, sport: str, market: str) -> float:
        return self.learning_engine.get_adaptive_threshold(sport, market)

    def should_bet(
        self,
        confidence: float,
        expected_value: float,
        implied_prob: float,
        sport: str,
        market: str,
    ) -> bool:
        """Gate: adaptive threshold + EV + sport-specific edge floor + calibration check."""
        required = self.get_threshold(sport, market)
        if confidence < required:
            return False
        if expected_value < self.MIN_EV:
            return False

        # Sport-specific edge floor
        edge_floor = self.SPORT_EDGE_FLOORS.get(sport, self.DEFAULT_EDGE_FLOOR)
        edge_vs_market = confidence - implied_prob
        if edge_vs_market < edge_floor:
            return False

        # Calibration check: reject if calibrated confidence < market implied prob
        calibrated = self._calibrate_confidence(confidence)
        if calibrated < implied_prob:
            print(
                f"  [V1-CAL] Rejected: raw={confidence:.0%} calibrates to {calibrated:.0%}, market={implied_prob:.0%}"
            )
            return False

        return True

    def post_run(self, results: Dict[str, Any]):
        """Update learning parameters based on recent performance."""
        try:
            from datetime import timedelta

            cutoff = (datetime.utcnow() - timedelta(days=30)).isoformat()
            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                FilterExpression="settled_at > :cutoff AND #status IN (:won, :lost)",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":cutoff": cutoff,
                    ":won": "won",
                    ":lost": "lost",
                },
            )
            bets = response.get("Items", [])
            if len(bets) < self.MIN_SAMPLE_SIZE:
                print(
                    f"Insufficient data for learning: {len(bets)} bets (need {self.MIN_SAMPLE_SIZE})"
                )
                return

            wins = sum(1 for b in bets if b.get("status") == "won")
            win_rate = wins / len(bets)

            total_wagered = sum(Decimal(str(b.get("bet_amount", 0))) for b in bets)
            total_profit = sum(Decimal(str(b.get("profit", 0))) for b in bets)
            roi = (
                (total_profit / total_wagered * 100)
                if total_wagered > 0
                else Decimal("0")
            )

            if win_rate > 0.60:
                adjustment = -0.02
            elif win_rate < 0.45:
                adjustment = 0.05
            else:
                current_adj = float(
                    self.learning_engine.params.get("min_confidence_adjustment", 0)
                )
                adjustment = -current_adj * 0.1

            perf_by_sport, perf_by_market, perf_by_prop_market = {}, {}, {}
            for bet in bets:
                sport = bet.get("sport", "unknown")
                market_key = bet.get("market_key", "unknown")
                won = bet.get("status") == "won"
                bet_amt = Decimal(str(bet.get("bet_amount", 0)))

                if sport not in perf_by_sport:
                    perf_by_sport[sport] = {"wins": 0, "total": 0}
                perf_by_sport[sport]["total"] += 1
                if won:
                    perf_by_sport[sport]["wins"] += 1

                if market_key not in perf_by_market:
                    perf_by_market[market_key] = {
                        "wins": 0,
                        "total": 0,
                        "wagered": Decimal("0"),
                        "returned": Decimal("0"),
                    }
                perf_by_market[market_key]["total"] += 1
                perf_by_market[market_key]["wagered"] += bet_amt
                if won:
                    perf_by_market[market_key]["wins"] += 1
                    perf_by_market[market_key]["returned"] += Decimal(
                        str(bet.get("payout", 0))
                    )

                if market_key.startswith("player_"):
                    if market_key not in perf_by_prop_market:
                        perf_by_prop_market[market_key] = {"wins": 0, "total": 0}
                    perf_by_prop_market[market_key]["total"] += 1
                    if won:
                        perf_by_prop_market[market_key]["wins"] += 1

            # Get deposits for true profit calc
            bankroll = self.bankroll_manager.bankroll
            try:
                dep_resp = self.table.query(
                    KeyConditionExpression=Key("pk").eq(self.pk)
                    & Key("sk").begins_with("DEPOSIT#"),
                )
                total_deposits = sum(
                    Decimal(str(d.get("amount", 0))) for d in dep_resp.get("Items", [])
                )
            except Exception:
                total_deposits = Decimal("0")
            true_profit = bankroll - self.WEEKLY_BUDGET - total_deposits

            self.learning_engine.params.update(
                {
                    "min_confidence_adjustment": Decimal(str(adjustment)),
                    "performance_by_sport": perf_by_sport,
                    "performance_by_market": perf_by_market,
                    "performance_by_prop_market": perf_by_prop_market,
                    "overall_win_rate": Decimal(str(win_rate)),
                    "total_bets_analyzed": len(bets),
                    "total_deposits": total_deposits,
                    "true_profit": true_profit,
                    "roi_percentage": roi,
                    "last_updated": datetime.utcnow().isoformat(),
                }
            )
            self.table.put_item(Item=self.learning_engine.params)
            print(
                f"Updated learning: win_rate={win_rate:.2%}, adjustment={adjustment:+.3f}"
            )

            if perf_by_prop_market:
                print("Prop market performance:")
                for market, stats in sorted(
                    perf_by_prop_market.items(),
                    key=lambda x: x[1]["wins"] / max(x[1]["total"], 1),
                    reverse=True,
                ):
                    wr = stats["wins"] / stats["total"] if stats["total"] > 0 else 0
                    print(f"  {market}: {stats['wins']}/{stats['total']} ({wr:.1%})")

            # Feature analysis + threshold optimization (ported from V2)
            try:
                from benny.outcome_analyzer import OutcomeAnalyzer
                from benny.threshold_optimizer import ThresholdOptimizer

                analyzer = OutcomeAnalyzer(self.table, self.pk)
                insights = analyzer.analyze_features()
                if "error" not in insights:
                    print(
                        f"Feature analysis: {insights['total_bets']} bets, top predictors: {[p['feature'] for p in insights.get('strongest_predictors', [])[:3]]}"
                    )
                    insights["timestamp"] = datetime.utcnow().isoformat()
                    analyzer.save_insights(insights)

                calibration = analyzer.analyze_confidence_calibration()
                if "error" not in calibration:
                    print(
                        f"Calibration error: {calibration['avg_calibration_error']:.1%}"
                    )
                    calibration["timestamp"] = datetime.utcnow().isoformat()
                    analyzer.save_calibration(calibration)

                optimizer = ThresholdOptimizer(self.table, self.pk)
                thresholds = optimizer.optimize_thresholds()
                if "error" not in thresholds:
                    print(
                        f"Optimal threshold: conf={thresholds['global']['optimal_min_confidence']:.0%}"
                    )
                    thresholds["timestamp"] = datetime.utcnow().isoformat()
                    optimizer.save_optimal_thresholds(thresholds)
            except Exception as e:
                print(f"Error in feature analysis: {e}")
        except Exception as e:
            print(f"Error updating learning parameters: {e}")
