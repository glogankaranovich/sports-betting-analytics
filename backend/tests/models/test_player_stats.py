"""Tests for PlayerStats model"""

import pytest
from unittest.mock import Mock, patch

from ml.models.player_stats import PlayerStatsModel
from ml.types import AnalysisResult


class TestPlayerStatsModel:
    @pytest.fixture
    def model(self):
        with patch('boto3.resource'):
            model = PlayerStatsModel()
            model.table = Mock()
            return model

    def test_analyze_game_not_supported(self, model):
        result = model.analyze_game_odds("game123", [], {})
        assert result is None

    def test_analyze_prop_insufficient_games(self, model):
        model.table.query.side_effect = [
            {"Items": [
                {"stats": {"PTS": "25", "MIN": "30"}},
                {"stats": {"PTS": "27", "MIN": "32"}},
            ]},
            {"Items": []}
        ]

        with patch('news_features.get_player_sentiment', return_value={"news_count": 0, "sentiment_score": 0, "impact_score": 0}):
            result = model.analyze_prop_odds({
                "sport": "basketball_nba",
                "player_name": "Player Name",
                "point": 25.5,
                "event_id": "evt123",
                "home_team": "Team A",
                "away_team": "Team B",
                "commence_time": "2024-01-15T19:00:00Z",
                "market_key": "player_points"
            })

        assert result is None

    def test_analyze_prop_player_injured(self, model):
        model.table.query.side_effect = [
            {"Items": [
                {"stats": {"PTS": "30", "MIN": "35"}},
                {"stats": {"PTS": "28", "MIN": "34"}},
                {"stats": {"PTS": "32", "MIN": "36"}},
                {"stats": {"PTS": "29", "MIN": "35"}},
                {"stats": {"PTS": "31", "MIN": "37"}},
            ]},
            {"Items": [{"status": "Out"}]}
        ]

        with patch('news_features.get_player_sentiment', return_value={"news_count": 0, "sentiment_score": 0, "impact_score": 0}):
            result = model.analyze_prop_odds({
                "sport": "basketball_nba",
                "player_name": "Injured Player",
                "point": 25.5,
                "event_id": "evt123",
                "home_team": "Team A",
                "away_team": "Team B",
                "commence_time": "2024-01-15T19:00:00Z",
                "market_key": "player_points"
            })

        assert result is None

    def test_analyze_prop_no_strong_streak(self, model):
        # Weak streak: Last 5 avg 27, Season avg 25 -> only 8% increase (below 25% threshold)
        model.table.query.side_effect = [
            {"Items": [
                {"stats": {"PTS": "28", "MIN": "35", "+/-": "3"}},
                {"stats": {"PTS": "27", "MIN": "34", "+/-": "2"}},
                {"stats": {"PTS": "26", "MIN": "33", "+/-": "4"}},
                {"stats": {"PTS": "28", "MIN": "36", "+/-": "1"}},
                {"stats": {"PTS": "26", "MIN": "35", "+/-": "5"}},
                {"stats": {"PTS": "24", "MIN": "32", "+/-": "2"}},
                {"stats": {"PTS": "25", "MIN": "31", "+/-": "1"}},
            ]},
            {"Items": []}
        ]

        with patch('news_features.get_player_sentiment', return_value={"news_count": 0, "sentiment_score": 0, "impact_score": 0}):
            result = model.analyze_prop_odds({
                "sport": "basketball_nba",
                "player_name": "Player Name",
                "point": 20.0,
                "event_id": "evt123",
                "home_team": "Team A",
                "away_team": "Team B",
                "commence_time": "2024-01-15T19:00:00Z",
                "market_key": "player_points"
            })

        assert result is None

    def test_analyze_prop_no_edge(self, model):
        # Strong streak but line too close: Last 5 avg 40, Season avg 25
        # Weighted: 36.25, Line 35 is between 36.25*0.865 (31.36) and 36.25*1.135 (41.14)
        model.table.query.side_effect = [
            {"Items": [
                {"stats": {"PTS": "42", "MIN": "35", "+/-": "8"}},
                {"stats": {"PTS": "40", "MIN": "34", "+/-": "5"}},
                {"stats": {"PTS": "38", "MIN": "33", "+/-": "6"}},
                {"stats": {"PTS": "41", "MIN": "36", "+/-": "7"}},
                {"stats": {"PTS": "39", "MIN": "35", "+/-": "4"}},
                {"stats": {"PTS": "22", "MIN": "32", "+/-": "2"}},
                {"stats": {"PTS": "24", "MIN": "31", "+/-": "1"}},
            ]},
            {"Items": []}
        ]

        with patch('news_features.get_player_sentiment', return_value={"news_count": 0, "sentiment_score": 0, "impact_score": 0}):
            result = model.analyze_prop_odds({
                "sport": "basketball_nba",
                "player_name": "Player Name",
                "point": 35.0,
                "event_id": "evt123",
                "home_team": "Team A",
                "away_team": "Team B",
                "commence_time": "2024-01-15T19:00:00Z",
                "market_key": "player_points"
            })

        assert result is None

    def test_analyze_prop_filters_low_minutes(self, model):
        # Only 4 games with >20 minutes after filtering
        model.table.query.side_effect = [
            {"Items": [
                {"stats": {"PTS": "30", "MIN": "35"}},
                {"stats": {"PTS": "5", "MIN": "8"}},  # Filtered
                {"stats": {"PTS": "28", "MIN": "34"}},
                {"stats": {"PTS": "32", "MIN": "36"}},
                {"stats": {"PTS": "29", "MIN": "35"}},
            ]},
            {"Items": []}
        ]

        with patch('news_features.get_player_sentiment', return_value={"news_count": 0, "sentiment_score": 0, "impact_score": 0}):
            result = model.analyze_prop_odds({
                "sport": "basketball_nba",
                "player_name": "Player Name",
                "point": 25.5,
                "event_id": "evt123",
                "home_team": "Team A",
                "away_team": "Team B",
                "commence_time": "2024-01-15T19:00:00Z",
                "market_key": "player_points"
            })

        assert result is None

    def test_get_player_stats_returns_data(self, model):
        model.table.query.return_value = {
            "Items": [
                {"stats": {"PTS": "30", "MIN": "35", "+/-": "5"}},
                {"stats": {"PTS": "28", "MIN": "34", "+/-": "4"}},
                {"stats": {"PTS": "32", "MIN": "36", "+/-": "6"}},
                {"stats": {"PTS": "29", "MIN": "35", "+/-": "3"}},
                {"stats": {"PTS": "31", "MIN": "37", "+/-": "5"}},
            ]
        }

        stats = model._get_player_stats("Player Name", "basketball_nba", "player_points", None)
        
        assert stats is not None
        assert stats['games'] == 5
        assert stats['avg'] == 30.0
        assert stats['last5'] == 30.0
        assert 'avg_plus_minus' in stats
