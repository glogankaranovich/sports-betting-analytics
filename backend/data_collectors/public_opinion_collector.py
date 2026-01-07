"""
Public Opinion Data Collector
Collects sentiment from Reddit, Twitter, and betting public
"""

from typing import Dict, List
from datetime import datetime
import logging
from .base_collector import BaseDataCollector, CollectionResult

logger = logging.getLogger(__name__)


class PublicOpinionCollector(BaseDataCollector):
    """Collects multi-platform public sentiment data"""

    def __init__(self):
        super().__init__("public_opinion", update_frequency_minutes=15)

    async def collect_data(self, sport: str, games: List[Dict]) -> CollectionResult:
        """Collect public opinion data for games"""
        try:
            opinion_data = {}
            records_collected = 0

            for game in games:
                # Collect sentiment from multiple sources
                reddit_sentiment = await self.collect_reddit_sentiment(game, sport)
                betting_public = await self.collect_betting_percentages(game)

                # Aggregate sentiment
                aggregated_sentiment = self.aggregate_sentiment(
                    {"reddit": reddit_sentiment, "betting_public": betting_public}
                )

                opinion_data[game["id"]] = aggregated_sentiment
                records_collected += 1

            quality_score = self.validate_data(opinion_data)

            return CollectionResult(
                success=True,
                data=opinion_data,
                error=None,
                timestamp=datetime.utcnow(),
                source="public_opinion_collector",
                data_quality_score=quality_score,
                records_collected=records_collected,
            )

        except Exception as e:
            logger.error(f"Public opinion collection failed: {e}")
            return CollectionResult(
                success=False,
                data=None,
                error=str(e),
                timestamp=datetime.utcnow(),
                source="public_opinion_collector",
                data_quality_score=0.0,
                records_collected=0,
            )

    async def collect_reddit_sentiment(self, game: Dict, sport: str) -> Dict:
        """Collect sentiment from Reddit (mock implementation)"""
        # Mock Reddit sentiment for now
        home_team = game.get("home_team", "").lower()
        away_team = game.get("away_team", "").lower()

        # Simple mock sentiment based on team names
        home_sentiment = 0.5 + (hash(home_team) % 100 - 50) / 200  # -0.25 to 0.25 range
        away_sentiment = 0.5 + (hash(away_team) % 100 - 50) / 200

        return {
            "posts_analyzed": 25,
            "home_team_sentiment": max(0, min(1, home_sentiment)),
            "away_team_sentiment": max(0, min(1, away_sentiment)),
            "betting_sentiment": (home_sentiment + away_sentiment) / 2,
            "volume_score": 0.6,
            "source": "reddit_mock",
        }

    async def collect_betting_percentages(self, game: Dict) -> Dict:
        """Collect betting public percentages (mock implementation)"""
        # Mock betting percentages
        home_team = game.get("home_team", "")

        # Simple mock based on team name hash
        home_percentage = 30 + (hash(home_team) % 40)  # 30-70% range
        away_percentage = 100 - home_percentage

        return {
            "home_team_percentage": home_percentage,
            "away_team_percentage": away_percentage,
            "total_bets": 1000 + (hash(home_team) % 5000),
            "sharp_money_percentage": 45 + (hash(home_team) % 20),  # 45-65%
            "source": "betting_public_mock",
        }

    def aggregate_sentiment(self, platform_data: Dict) -> Dict:
        """Aggregate sentiment from multiple platforms"""
        reddit = platform_data.get("reddit", {})
        betting = platform_data.get("betting_public", {})

        # Weight different sources
        reddit_weight = 0.4
        betting_weight = 0.6

        # Calculate composite sentiment
        home_sentiment = (
            reddit.get("home_team_sentiment", 0.5) * reddit_weight
            + (betting.get("home_team_percentage", 50) / 100) * betting_weight
        )

        away_sentiment = (
            reddit.get("away_team_sentiment", 0.5) * reddit_weight
            + (betting.get("away_team_percentage", 50) / 100) * betting_weight
        )

        # Calculate contrarian indicators
        public_fade_score = self.calculate_public_fade_score(betting)

        return {
            "composite_home_sentiment": round(home_sentiment, 3),
            "composite_away_sentiment": round(away_sentiment, 3),
            "sentiment_differential": round(home_sentiment - away_sentiment, 3),
            "public_fade_score": public_fade_score,
            "data_sources": ["reddit", "betting_public"],
            "reddit_data": reddit,
            "betting_data": betting,
            "collected_at": datetime.utcnow().isoformat(),
        }

    def calculate_public_fade_score(self, betting_data: Dict) -> float:
        """Calculate contrarian 'fade the public' score"""
        home_pct = betting_data.get("home_team_percentage", 50)

        # Higher score when public is heavily on one side
        if home_pct > 70:
            return 0.8  # Fade home team
        elif home_pct < 30:
            return 0.8  # Fade away team
        elif 45 <= home_pct <= 55:
            return 0.1  # Balanced, no fade opportunity
        else:
            return 0.4  # Moderate fade opportunity

    def validate_data(self, data: Dict) -> float:
        """Validate public opinion data quality"""
        if not data:
            return 0.0

        total_games = len(data)
        valid_games = 0

        required_fields = [
            "composite_home_sentiment",
            "composite_away_sentiment",
            "public_fade_score",
        ]

        for game_data in data.values():
            if all(field in game_data for field in required_fields):
                valid_games += 1

        return valid_games / total_games if total_games > 0 else 0.0
