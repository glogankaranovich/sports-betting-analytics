"""News Model - Predict based on news sentiment analysis"""

import logging
from typing import Dict, List

from ml.models.base import BaseModel
from ml.types import AnalysisResult

logger = logging.getLogger(__name__)


class NewsModel(BaseModel):
    """Model based purely on news sentiment analysis"""

    def analyze_game_odds(
        self, game_id: str, odds_items: List[Dict], game_info: Dict
    ) -> AnalysisResult:
        try:
            from news_features import get_team_sentiment

            sport = game_info.get("sport")
            home_team = game_info.get("home_team")
            away_team = game_info.get("away_team")

            if not all([sport, home_team, away_team]):
                return None

            home_sentiment = get_team_sentiment(sport, home_team)
            away_sentiment = get_team_sentiment(sport, away_team)

            if home_sentiment["news_count"] == 0 and away_sentiment["news_count"] == 0:
                return None

            sentiment_diff = (
                home_sentiment["sentiment_score"] - away_sentiment["sentiment_score"]
            )
            avg_impact = (
                home_sentiment["impact_score"] + away_sentiment["impact_score"]
            ) / 2

            if abs(sentiment_diff) < 0.05:
                return None

            prediction = home_team if sentiment_diff > 0 else away_team
            confidence = min(0.75, 0.5 + (abs(sentiment_diff) * avg_impact * 0.5))

            return AnalysisResult(
                game_id=game_id,
                model="news",
                analysis_type="game",
                sport=sport,
                home_team=home_team,
                away_team=away_team,
                commence_time=game_info.get("commence_time"),
                prediction=prediction,
                confidence=confidence,
                reasoning=f"Recent news favors {prediction}: {home_sentiment['news_count']} home stories, {away_sentiment['news_count']} away stories. Positive buzz around {prediction}",
                recommended_odds=-110,
            )
        except Exception as e:
            logger.error(f"Error in news model: {e}")
            return None

    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        return None
