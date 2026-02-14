"""Unit tests for news features"""
import os
import unittest
from unittest.mock import patch
from decimal import Decimal

os.environ["DYNAMODB_TABLE"] = "test-table"

from news_features import (  # noqa: E402
    get_news_sentiment,
    get_player_sentiment,
    get_team_sentiment,
    enrich_game_with_news,
)


class TestNewsFeatures(unittest.TestCase):
    """Test news sentiment extraction"""

    @patch("news_features.table")
    def test_get_news_sentiment_no_news(self, mock_table):
        """Should return zeros when no news found"""
        mock_table.query.return_value = {"Items": []}

        result = get_news_sentiment("basketball_nba", ["Lakers"])

        self.assertEqual(result["sentiment_score"], 0.0)
        self.assertEqual(result["impact_score"], 0.0)
        self.assertEqual(result["news_count"], 0)

    @patch("news_features.table")
    def test_get_news_sentiment_with_news(self, mock_table):
        """Should calculate sentiment from news items"""
        mock_table.query.return_value = {
            "Items": [
                {
                    "headline": "Lakers win big game",
                    "description": "Great performance",
                    "sentiment_positive": Decimal("0.8"),
                    "sentiment_negative": Decimal("0.1"),
                    "impact": "high",
                },
                {
                    "headline": "Lakers injury report",
                    "description": "Player questionable",
                    "sentiment_positive": Decimal("0.3"),
                    "sentiment_negative": Decimal("0.6"),
                    "impact": "medium",
                },
            ]
        }

        result = get_news_sentiment("basketball_nba", ["Lakers"])

        self.assertGreater(result["sentiment_score"], 0)
        self.assertGreater(result["impact_score"], 0)
        self.assertEqual(result["news_count"], 2)

    @patch("news_features.get_news_sentiment")
    def test_get_player_sentiment(self, mock_get_news):
        """Should call get_news_sentiment with player name"""
        mock_get_news.return_value = {
            "sentiment_score": 0.5,
            "impact_score": 2.0,
            "news_count": 3,
        }

        result = get_player_sentiment("basketball_nba", "LeBron James")

        mock_get_news.assert_called_once_with("basketball_nba", ["LeBron James"], 48)
        self.assertEqual(result["sentiment_score"], 0.5)

    @patch("news_features.get_news_sentiment")
    def test_get_team_sentiment(self, mock_get_news):
        """Should call get_news_sentiment with team name"""
        mock_get_news.return_value = {
            "sentiment_score": -0.2,
            "impact_score": 1.5,
            "news_count": 2,
        }

        result = get_team_sentiment("basketball_nba", "Lakers")

        mock_get_news.assert_called_once_with("basketball_nba", ["Lakers"], 48)
        self.assertEqual(result["sentiment_score"], -0.2)

    @patch("news_features.get_team_sentiment")
    def test_enrich_game_with_news(self, mock_get_sentiment):
        """Should add news sentiment to game_info"""
        mock_get_sentiment.side_effect = [
            {"sentiment_score": 0.3, "impact_score": 2.0, "news_count": 3},
            {"sentiment_score": -0.1, "impact_score": 1.5, "news_count": 2},
        ]

        game_info = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Celtics",
        }

        result = enrich_game_with_news(game_info)

        self.assertEqual(result["home_news_sentiment"], 0.3)
        self.assertEqual(result["home_news_impact"], 2.0)
        self.assertEqual(result["away_news_sentiment"], -0.1)
        self.assertEqual(result["away_news_impact"], 1.5)

    @patch("news_features.get_team_sentiment")
    def test_enrich_game_with_news_error(self, mock_get_sentiment):
        """Should set defaults on error"""
        mock_get_sentiment.side_effect = Exception("DB error")

        game_info = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Celtics",
        }

        result = enrich_game_with_news(game_info)

        self.assertEqual(result["home_news_sentiment"], 0.0)
        self.assertEqual(result["home_news_impact"], 0.0)
        self.assertEqual(result["away_news_sentiment"], 0.0)
        self.assertEqual(result["away_news_impact"], 0.0)


if __name__ == "__main__":
    unittest.main()
