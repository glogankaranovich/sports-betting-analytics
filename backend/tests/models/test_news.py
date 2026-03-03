"""Tests for News model"""

import pytest
from unittest.mock import Mock, patch

from ml.models.news import NewsModel
from ml.types import AnalysisResult


class TestNewsModel:
    @pytest.fixture
    def model(self):
        return NewsModel()

    def test_analyze_game_positive_home_sentiment(self, model):
        with patch('news_features.get_team_sentiment') as mock_sentiment:
            mock_sentiment.side_effect = [
                {"news_count": 5, "sentiment_score": 0.7, "impact_score": 0.8},
                {"news_count": 3, "sentiment_score": 0.4, "impact_score": 0.6}
            ]

            result = model.analyze_game_odds(
                "game123",
                [],
                {
                    "sport": "basketball_nba",
                    "home_team": "Boston Celtics",
                    "away_team": "Los Angeles Lakers",
                    "commence_time": "2024-01-15T19:00:00Z"
                }
            )

            assert result.prediction == "Boston Celtics"
            assert result.confidence > 0.5
            assert "news favors" in result.reasoning.lower()

    def test_analyze_game_positive_away_sentiment(self, model):
        with patch('news_features.get_team_sentiment') as mock_sentiment:
            mock_sentiment.side_effect = [
                {"news_count": 2, "sentiment_score": 0.3, "impact_score": 0.5},
                {"news_count": 6, "sentiment_score": 0.8, "impact_score": 0.9}
            ]

            result = model.analyze_game_odds(
                "game123",
                [],
                {
                    "sport": "basketball_nba",
                    "home_team": "Boston Celtics",
                    "away_team": "Los Angeles Lakers",
                    "commence_time": "2024-01-15T19:00:00Z"
                }
            )

            assert result.prediction == "Los Angeles Lakers"
            assert result.confidence > 0.5

    def test_analyze_game_no_news(self, model):
        with patch('news_features.get_team_sentiment') as mock_sentiment:
            mock_sentiment.side_effect = [
                {"news_count": 0, "sentiment_score": 0.0, "impact_score": 0.0},
                {"news_count": 0, "sentiment_score": 0.0, "impact_score": 0.0}
            ]

            result = model.analyze_game_odds(
                "game123",
                [],
                {
                    "sport": "basketball_nba",
                    "home_team": "Boston Celtics",
                    "away_team": "Los Angeles Lakers",
                    "commence_time": "2024-01-15T19:00:00Z"
                }
            )

            assert result is None

    def test_analyze_game_minimal_sentiment_diff(self, model):
        with patch('news_features.get_team_sentiment') as mock_sentiment:
            mock_sentiment.side_effect = [
                {"news_count": 3, "sentiment_score": 0.52, "impact_score": 0.6},
                {"news_count": 3, "sentiment_score": 0.50, "impact_score": 0.6}
            ]

            result = model.analyze_game_odds(
                "game123",
                [],
                {
                    "sport": "basketball_nba",
                    "home_team": "Boston Celtics",
                    "away_team": "Los Angeles Lakers",
                    "commence_time": "2024-01-15T19:00:00Z"
                }
            )

            assert result is None

    def test_analyze_prop_not_supported(self, model):
        result = model.analyze_prop_odds({})
        assert result is None
