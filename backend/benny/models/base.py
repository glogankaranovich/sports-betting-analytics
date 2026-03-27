"""Base interface for Benny betting models"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, Any, List


class BennyModelBase(ABC):
    """Abstract base class for Benny betting models.
    
    Each model implements its own:
    - AI prompts (how to ask for predictions)
    - Bet sizing (Kelly vs flat)
    - Threshold logic (adaptive vs fixed)
    - Post-run learning
    """

    @property
    @abstractmethod
    def pk(self) -> str:
        """DynamoDB partition key for this model's data"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """Model version identifier (v1, v2, v3)"""
        pass

    @abstractmethod
    def build_game_prompt(
        self,
        game_data: Dict,
        context: Dict[str, Any],
    ) -> str:
        """Build the AI prompt for game analysis.
        
        Args:
            game_data: Game info (teams, odds, commence_time)
            context: Gathered data (elo, form, injuries, weather, etc.)
        
        Returns:
            Prompt string for the AI model
        """
        pass

    @abstractmethod
    def build_prop_prompt(
        self,
        prop_data: Dict,
        player_stats: Dict,
        player_trends: Dict,
        matchup_data: Dict,
    ) -> str:
        """Build the AI prompt for prop analysis."""
        pass

    @abstractmethod
    def calculate_bet_size(
        self,
        confidence: float,
        odds: float,
        bankroll: Decimal,
    ) -> Decimal:
        """Calculate bet size for an opportunity.
        
        Args:
            confidence: AI's stated confidence (0-1)
            odds: American odds
            bankroll: Current bankroll
        
        Returns:
            Bet size in dollars
        """
        pass

    @abstractmethod
    def get_threshold(self, sport: str, market: str) -> float:
        """Get minimum confidence threshold for a sport/market combo."""
        pass

    @abstractmethod
    def should_bet(
        self,
        confidence: float,
        expected_value: float,
        implied_prob: float,
        sport: str,
        market: str,
    ) -> bool:
        """Determine if an opportunity meets betting criteria.
        
        Args:
            confidence: AI's stated confidence
            expected_value: Calculated EV
            implied_prob: Market's implied probability
            sport: Sport key
            market: Market key (h2h, spread, player_points, etc.)
        
        Returns:
            True if should place bet
        """
        pass

    @abstractmethod
    def post_run(self, results: Dict[str, Any]):
        """Called after each run for learning/tracking.
        
        Args:
            results: Summary of bets placed, outcomes, etc.
        """
        pass

    def get_min_bet(self) -> Decimal:
        """Minimum bet size. Override if needed."""
        return Decimal("5.00")

    def get_max_bet_pct(self) -> float:
        """Maximum bet as percentage of bankroll. Override if needed."""
        return 0.20

    _recent_losses_cache = None
    _settled_bets_cache = None

    def _get_settled_bets(self):
        """Fetch and cache all settled bets (newest first). Single DB query per run."""
        if self._settled_bets_cache is not None:
            return self._settled_bets_cache
        try:
            from boto3.dynamodb.conditions import Key

            response = self.table.query(
                KeyConditionExpression=Key("pk").eq(self.pk)
                & Key("sk").begins_with("BET#"),
                FilterExpression="#s IN (:w, :l)",
                ExpressionAttributeNames={"#s": "status"},
                ExpressionAttributeValues={":w": "won", ":l": "lost"},
                ScanIndexForward=False,
                Limit=200,
            )
            self._settled_bets_cache = response.get("Items", [])
        except Exception:
            self._settled_bets_cache = []
        return self._settled_bets_cache

    def _get_recent_losses_text(self, sport: str = None, limit: int = 5) -> str:
        """Recent losses per sport — shows the AI its specific mistakes."""
        bets = self._get_settled_bets()
        losses = [b for b in bets if b.get("status") == "lost"]
        if sport:
            losses = [b for b in losses if b.get("sport") == sport]
        losses = losses[:limit]
        if not losses:
            return ""
        lines = [f"YOUR RECENT LOSSES{f' IN {sport}' if sport else ''} (learn from these — do not repeat):"]
        for b in losses:
            pred = b.get("prediction", "?")
            conf = float(b.get("confidence", 0))
            reasoning = (b.get("ai_reasoning") or "")[:120]
            lines.append(f"  ✗ {pred} — you said {conf:.0%} confident")
            if reasoning:
                lines.append(f"    Reasoning: {reasoning}")
        return "\n".join(lines)

    def _get_recent_wins_text(self, sport: str = None, limit: int = 5) -> str:
        """Recent wins per sport — reinforces what works."""
        bets = self._get_settled_bets()
        wins = [b for b in bets if b.get("status") == "won"]
        if sport:
            wins = [b for b in wins if b.get("sport") == sport]
        wins = wins[:limit]
        if not wins:
            return ""
        lines = [f"YOUR RECENT WINS{f' IN {sport}' if sport else ''} (repeat these patterns):"]
        for b in wins:
            pred = b.get("prediction", "?")
            conf = float(b.get("confidence", 0))
            reasoning = (b.get("ai_reasoning") or "")[:120]
            lines.append(f"  ✓ {pred} — you said {conf:.0%} confident")
            if reasoning:
                lines.append(f"    Reasoning: {reasoning}")
        return "\n".join(lines)

    def _get_factor_track_record(self) -> str:
        """Which key_factors correlate with wins vs losses."""
        bets = self._get_settled_bets()
        if len(bets) < 10:
            return ""
        factor_perf = {}
        for b in bets:
            won = b.get("status") == "won"
            for f in b.get("ai_key_factors", []):
                if f not in factor_perf:
                    factor_perf[f] = {"w": 0, "t": 0}
                factor_perf[f]["t"] += 1
                if won:
                    factor_perf[f]["w"] += 1
        # Only show factors with 3+ occurrences
        relevant = {f: v for f, v in factor_perf.items() if v["t"] >= 3}
        if not relevant:
            return ""
        good = [(f, v) for f, v in relevant.items() if v["w"] / v["t"] >= 0.55]
        bad = [(f, v) for f, v in relevant.items() if v["w"] / v["t"] <= 0.40]
        good.sort(key=lambda x: x[1]["w"] / x[1]["t"], reverse=True)
        bad.sort(key=lambda x: x[1]["w"] / x[1]["t"])
        lines = ["FACTOR TRACK RECORD (which reasoning factors actually predict wins):"]
        for f, v in good[:5]:
            lines.append(f"  ✓ {f}: {v['w']}/{v['t']} ({v['w']/v['t']:.0%}) — trust this factor")
        for f, v in bad[:5]:
            lines.append(f"  ✗ {f}: {v['w']}/{v['t']} ({v['w']/v['t']:.0%}) — this factor misleads you")
        return "\n".join(lines)

    def _get_sport_market_record(self, sport: str) -> str:
        """Win rate by market for a given sport. Raw numbers."""
        bets = self._get_settled_bets()
        sport_bets = [b for b in bets if b.get("sport") == sport]
        if not sport_bets:
            return ""
        by_market = {}
        for b in sport_bets:
            m = b.get("market_key", "?")
            if m not in by_market:
                by_market[m] = {"w": 0, "t": 0}
            by_market[m]["t"] += 1
            if b.get("status") == "won":
                by_market[m]["w"] += 1
        lines = [f"YOUR RECORD IN {sport}:"]
        for m, v in sorted(by_market.items(), key=lambda x: x[1]["t"], reverse=True):
            wr = v["w"] / v["t"] if v["t"] else 0
            lines.append(f"  {m}: {v['w']}/{v['t']} ({wr:.0%})")
        return "\n".join(lines)
