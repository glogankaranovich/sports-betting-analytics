"""
Team Momentum Data Collector
Collects recent performance trends and momentum indicators
"""

from typing import Dict, List
from datetime import datetime
import logging
from .base_collector import BaseDataCollector, CollectionResult
from dao import BettingDAO

logger = logging.getLogger(__name__)


class TeamMomentumCollector(BaseDataCollector):
    """Collects team momentum and recent performance data"""

    def __init__(self):
        super().__init__("team_momentum", update_frequency_minutes=60)
        self.dao = BettingDAO()

    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect team momentum data for all games"""
        try:
            momentum_data = {}
            records_collected = 0

            for game in games:
                home_team = game["home_team"]
                away_team = game["away_team"]

                # Calculate momentum for both teams
                home_momentum = await self.calculate_team_momentum(home_team, sport)
                away_momentum = await self.calculate_team_momentum(away_team, sport)

                momentum_data[game["id"]] = {
                    "home_team_momentum": home_momentum,
                    "away_team_momentum": away_momentum,
                    "momentum_differential": home_momentum["composite_score"]
                    - away_momentum["composite_score"],
                    "collected_at": datetime.utcnow().isoformat(),
                }
                records_collected += 1

            quality_score = self.validate_data(momentum_data)

            return CollectionResult(
                success=True,
                data=momentum_data,
                error=None,
                timestamp=datetime.utcnow(),
                source="team_momentum_collector",
                data_quality_score=quality_score,
                records_collected=records_collected,
            )

        except Exception as e:
            return CollectionResult(
                success=False,
                data=None,
                error=str(e),
                timestamp=datetime.utcnow(),
                source="team_momentum_collector",
                data_quality_score=0.0,
                records_collected=0,
            )

    async def calculate_team_momentum(self, team: str, sport: str) -> Dict:
        """Calculate comprehensive team momentum metrics"""

        # Get recent games (last 10 for NBA, last 4 for NFL)
        lookback_games = 10 if sport == "basketball_nba" else 4
        recent_games = await self.get_recent_games(team, sport, lookback_games)

        if not recent_games:
            return self.get_default_momentum()

        momentum_metrics = {
            "win_streak": self.calculate_win_streak(recent_games),
            "recent_record": self.calculate_recent_record(recent_games),
            "point_differential_trend": self.calculate_point_diff_trend(recent_games),
            "ats_record": self.calculate_ats_record(recent_games),
            "games_analyzed": len(recent_games),
            "composite_score": 0.0,
        }

        # Calculate composite momentum score
        momentum_metrics["composite_score"] = self.calculate_composite_momentum(
            momentum_metrics
        )

        return momentum_metrics

    async def get_recent_games(self, team: str, sport: str, count: int) -> List[Dict]:
        """Get recent completed games for a team"""
        try:
            # Query DynamoDB for recent games
            # This would integrate with existing game data
            # For now, return mock data structure
            return []
        except Exception as e:
            logger.error(f"Failed to get recent games for {team}: {e}")
            return []

    def calculate_win_streak(self, games: List[Dict]) -> int:
        """Calculate current win streak (positive) or loss streak (negative)"""
        if not games:
            return 0

        streak = 0
        last_result = None

        # Games should be ordered by date (most recent first)
        for game in games:
            won = game.get("team_won", False)

            if last_result is None:
                last_result = won
                streak = 1 if won else -1
            elif won == last_result:
                streak += 1 if won else -1
            else:
                break

        return streak

    def calculate_recent_record(self, games: List[Dict]) -> Dict:
        """Calculate win-loss record for recent games"""
        if not games:
            return {"wins": 0, "losses": 0, "win_percentage": 0.5}

        wins = sum(1 for game in games if game.get("team_won", False))
        losses = len(games) - wins
        win_pct = wins / len(games) if games else 0.5

        return {"wins": wins, "losses": losses, "win_percentage": win_pct}

    def calculate_point_diff_trend(self, games: List[Dict]) -> float:
        """Calculate trend in point differential (positive = improving)"""
        if len(games) < 2:
            return 0.0

        point_diffs = [game.get("point_differential", 0) for game in games]

        # Simple linear trend calculation without numpy
        n = len(point_diffs)
        x_mean = (n - 1) / 2  # Mean of 0, 1, 2, ..., n-1
        y_mean = sum(point_diffs) / n

        numerator = sum((i - x_mean) * (y - y_mean) for i, y in enumerate(point_diffs))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator == 0:
            return 0.0

        trend = numerator / denominator
        return round(trend, 3)

    def calculate_ats_record(self, games: List[Dict]) -> Dict:
        """Calculate against-the-spread record"""
        if not games:
            return {"ats_wins": 0, "ats_losses": 0, "ats_percentage": 0.5}

        ats_wins = sum(1 for game in games if game.get("covered_spread", False))
        ats_losses = len(games) - ats_wins
        ats_pct = ats_wins / len(games) if games else 0.5

        return {
            "ats_wins": ats_wins,
            "ats_losses": ats_losses,
            "ats_percentage": ats_pct,
        }

    def calculate_composite_momentum(self, metrics: Dict) -> float:
        """Calculate composite momentum score (0-1, higher = better momentum)"""

        # Normalize individual components
        win_pct_score = metrics["recent_record"]["win_percentage"]

        # Win streak component (normalize to 0-1)
        streak = metrics["win_streak"]
        max_streak = 5  # Assume max meaningful streak is 5
        streak_score = max(0, min(1, (streak + max_streak) / (2 * max_streak)))

        # Point differential trend (normalize around 0)
        trend = metrics["point_differential_trend"]
        trend_score = max(
            0, min(1, (trend + 10) / 20)
        )  # Assume +/-10 is meaningful range

        # ATS performance
        ats_score = metrics["ats_record"]["ats_percentage"]

        # Weighted combination
        composite = (
            win_pct_score * 0.4
            + streak_score * 0.3
            + trend_score * 0.2
            + ats_score * 0.1
        )

        return round(composite, 3)

    def get_default_momentum(self) -> Dict:
        """Return default momentum when no data available"""
        return {
            "win_streak": 0,
            "recent_record": {"wins": 0, "losses": 0, "win_percentage": 0.5},
            "point_differential_trend": 0.0,
            "ats_record": {"ats_wins": 0, "ats_losses": 0, "ats_percentage": 0.5},
            "games_analyzed": 0,
            "composite_score": 0.5,
        }

    def validate_data(self, data: Dict) -> float:
        """Validate momentum data quality"""
        if not data:
            return 0.0

        required_fields = [
            "win_streak",
            "recent_record",
            "point_differential_trend",
            "composite_score",
        ]

        total_checks = 0
        passed_checks = 0

        for game_data in data.values():
            for team_type in ["home_team_momentum", "away_team_momentum"]:
                if team_type not in game_data:
                    continue

                team_data = game_data[team_type]
                for field in required_fields:
                    total_checks += 1
                    if field in team_data and team_data[field] is not None:
                        passed_checks += 1

        return passed_checks / total_checks if total_checks > 0 else 0.0
