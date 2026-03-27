"""Programmatic confidence scorer — replaces LLM-stated confidence for V3.

Computes confidence from quantitative signals that the AI prompt also sees.
Each signal is scored 0-1, then combined via weighted sum into a final confidence.

Design: base_rate (market implied prob) + bonus for each confirming signal.
This means we NEVER bet against the data — confidence is grounded in reality.
"""
from typing import Dict, Any


def score_game(context: Dict[str, Any], pick: str, game_data: Dict) -> float:
    """Compute confidence for a game bet from quantitative signals.

    Args:
        context: The context dict built in _ai_analyze_game (elo, form, injuries, etc.)
        pick: The AI's pick string (e.g. "Los Angeles Lakers (Moneyline)")
        game_data: Game info with home_team, away_team, sport

    Returns:
        Confidence float between 0.50 and 0.90
    """
    home = game_data["home_team"].lower()
    away = game_data["away_team"].lower()
    pick_lower = pick.lower()

    # Determine which side was picked
    picked_home = home in pick_lower
    picked_away = away in pick_lower
    if not picked_home and not picked_away:
        return 0.50  # Can't determine side

    # --- Signal 1: Elo edge (0-1) ---
    home_elo = float(context.get("home_elo", 1500))
    away_elo = float(context.get("away_elo", 1500))
    elo_diff = home_elo - away_elo  # positive = home stronger
    if picked_away:
        elo_diff = -elo_diff
    # Scale: 0 at diff=0, 1.0 at diff>=300
    elo_signal = min(max(elo_diff / 300, 0), 1.0)

    # --- Signal 2: Form edge (0-1) ---
    form_signal = _score_form(context, picked_home)

    # --- Signal 3: Injury edge (0-1) ---
    injury_signal = _score_injuries(context, picked_home)

    # --- Signal 4: H2H edge (0-1) ---
    h2h_signal = _score_h2h(context, picked_home, home, away)

    # --- Signal 5: Market alignment (0-1) ---
    # Are we picking the market favorite? If so, that's confirming.
    home_prob = float(context.get("home_prob", 0.5))
    away_prob = float(context.get("away_prob", 0.5))
    picked_prob = home_prob if picked_home else away_prob
    # 1.0 if we're picking a 70%+ favorite, 0 if picking a 30% underdog
    market_signal = min(max((picked_prob - 0.30) / 0.40, 0), 1.0)

    # --- Combine ---
    # Weights reflect predictive power (elo and market are strongest)
    weights = {
        "elo": 0.30,
        "form": 0.15,
        "injury": 0.10,
        "h2h": 0.10,
        "market": 0.35,
    }
    raw = (
        weights["elo"] * elo_signal
        + weights["form"] * form_signal
        + weights["injury"] * injury_signal
        + weights["h2h"] * h2h_signal
        + weights["market"] * market_signal
    )

    # Map raw (0-1) to confidence range (0.50-0.90)
    confidence = 0.50 + raw * 0.40
    return round(confidence, 2)


def score_prop(prop_data: Dict, player_stats: Dict, player_trends: Dict,
               matchup_data: Dict, pick: str) -> float:
    """Compute confidence for a prop bet from player data.

    Args:
        prop_data: Prop info (player, market, line, odds)
        player_stats: Aggregated season stats
        player_trends: Recent trend data
        matchup_data: Performance vs opponent
        pick: AI's pick string (e.g. "Over 25.5 (Points)")

    Returns:
        Confidence float between 0.50 and 0.90
    """
    pick_lower = pick.lower()
    is_over = "over" in pick_lower

    line = float(prop_data.get("line", 0)) if prop_data.get("line") else 0
    if not line:
        return 0.50

    market = prop_data.get("market", "")

    # --- Signal 1: Season avg vs line (0-1) ---
    avg_signal = _score_stat_vs_line(player_stats, market, line, is_over, suffix="_avg")

    # --- Signal 2: Last 5 trend vs line (0-1) ---
    last5_signal = _score_stat_vs_line(player_stats, market, line, is_over, suffix="_last5")

    # --- Signal 3: Trend direction (0-1) ---
    trend_signal = 0.5
    trend = player_trends.get("trend", "")
    if (is_over and trend == "hot") or (not is_over and trend == "cold"):
        trend_signal = 1.0
    elif (is_over and trend == "cold") or (not is_over and trend == "hot"):
        trend_signal = 0.0

    # --- Signal 4: Matchup history (0-1) ---
    matchup_signal = 0.5
    games_vs = matchup_data.get("games_vs_opponent", 0)
    if games_vs >= 2:
        matchup_signal = 0.7  # Some history is mildly confirming

    # --- Combine ---
    weights = {"avg": 0.35, "last5": 0.30, "trend": 0.20, "matchup": 0.15}
    raw = (
        weights["avg"] * avg_signal
        + weights["last5"] * last5_signal
        + weights["trend"] * trend_signal
        + weights["matchup"] * matchup_signal
    )

    confidence = 0.50 + raw * 0.40
    return round(confidence, 2)


# --- Helper functions ---

_MARKET_STAT_MAP = {
    "player_points": "PTS",
    "player_rebounds": "REB",
    "player_assists": "AST",
    "player_threes": "3PM",
    "player_steals": "STL",
    "player_blocks": "BLK",
}


def _score_stat_vs_line(stats: Dict, market: str, line: float,
                        is_over: bool, suffix: str) -> float:
    """Score how much a stat average supports the pick vs the line."""
    stat_key = _MARKET_STAT_MAP.get(market, "")
    if not stat_key:
        return 0.5
    val = stats.get(f"{stat_key}{suffix}", 0)
    if not val:
        return 0.5
    diff = float(val) - line
    if not is_over:
        diff = -diff
    # Scale: 0 at diff=-5, 0.5 at diff=0, 1.0 at diff=+5
    return min(max((diff + 5) / 10, 0), 1.0)


def _score_form(context: Dict, picked_home: bool) -> float:
    """Score recent form advantage for the picked side."""
    picked_form = context.get("home_form" if picked_home else "away_form", {})
    opp_form = context.get("away_form" if picked_home else "home_form", {})

    def _parse_record(form):
        record = form.get("record", "")
        if "-" not in record:
            return 0, 0
        parts = record.split("-")
        try:
            return int(parts[0]), int(parts[1])
        except (ValueError, IndexError):
            return 0, 0

    pw, pl = _parse_record(picked_form)
    ow, ol = _parse_record(opp_form)

    picked_wr = pw / (pw + pl) if (pw + pl) > 0 else 0.5
    opp_wr = ow / (ow + ol) if (ow + ol) > 0 else 0.5

    diff = picked_wr - opp_wr  # -1 to +1
    return min(max((diff + 1) / 2, 0), 1.0)  # map to 0-1


def _score_injuries(context: Dict, picked_home: bool) -> float:
    """Score injury advantage — fewer injuries on picked side is better."""
    picked_inj = context.get("home_injuries" if picked_home else "away_injuries", [])
    opp_inj = context.get("away_injuries" if picked_home else "home_injuries", [])

    picked_count = len(picked_inj) if picked_inj else 0
    opp_count = len(opp_inj) if opp_inj else 0

    diff = opp_count - picked_count  # positive = opponent has more injuries
    # Scale: 0 at diff=-3, 0.5 at diff=0, 1.0 at diff=+3
    return min(max((diff + 3) / 6, 0), 1.0)


def _score_h2h(context: Dict, picked_home: bool, home: str, away: str) -> float:
    """Score head-to-head history advantage."""
    h2h = context.get("h2h_history", [])
    if not h2h:
        return 0.5  # No data = neutral

    picked_team = home if picked_home else away
    wins = sum(1 for g in h2h if picked_team in g.get("winner", "").lower())
    total = len(h2h)
    if total == 0:
        return 0.5
    return wins / total  # Already 0-1
