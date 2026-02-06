"""
Unit tests for Matchup Model
"""

from unittest.mock import MagicMock

import pytest

from ml.models import MatchupModel


class TestMatchupModel:
    """Test cases for MatchupModel"""

    @pytest.fixture
    def mock_table(self):
        """Create a mock DynamoDB table"""
        return MagicMock()

    @pytest.fixture
    def model(self, mock_table):
        """Create a MatchupModel instance with mocked table"""
        return MatchupModel(dynamodb_table=mock_table)

    def test_strong_h2h_advantage(self, model, mock_table):
        """Test prediction when team has strong head-to-head advantage"""
        # Mock H2H data - home team won 8 of 10 recent games
        mock_table.query.side_effect = [
            {
                "Items": [
                    {"winner": "Lakers"},
                    {"winner": "Lakers"},
                    {"winner": "Lakers"},
                    {"winner": "Lakers"},
                    {"winner": "Celtics"},
                    {"winner": "Lakers"},
                    {"winner": "Lakers"},
                    {"winner": "Celtics"},
                    {"winner": "Lakers"},
                    {"winner": "Lakers"},
                ]
            },
            {"Items": [{"points_per_game": 115, "points_allowed_per_game": 105}]},
            {"Items": [{"points_per_game": 108, "points_allowed_per_game": 110}]},
        ]

        game_info = {
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Celtics",
            "commence_time": "2026-01-25T00:00:00Z",
        }

        result = model.analyze_game_odds("game123", [], game_info)

        assert result.prediction == "Lakers"
        assert result.confidence > 0.5
        assert "H2H" in result.reasoning

    def test_no_historical_data(self, model, mock_table):
        """Test when no historical matchup data exists"""
        mock_table.query.side_effect = [
            {"Items": []},  # No H2H data
            {"Items": [{"points_per_game": 110, "points_allowed_per_game": 108}]},
            {"Items": [{"points_per_game": 109, "points_allowed_per_game": 107}]},
        ]

        game_info = {
            "sport": "basketball_nba",
            "home_team": "Team A",
            "away_team": "Team B",
            "commence_time": "2026-01-25T00:00:00Z",
        }

        result = model.analyze_game_odds("game123", [], game_info)

        # Should still make prediction based on style matchup
        assert result.prediction in ["Team A", "Team B"]
        assert 0.3 <= result.confidence <= 0.85

    def test_style_matchup_advantage(self, model, mock_table):
        """Test when style matchup favors one team"""
        mock_table.query.side_effect = [
            {"Items": []},  # No H2H data
            {"Items": [{"points_per_game": 125, "points_allowed_per_game": 95}]},
            {"Items": [{"points_per_game": 90, "points_allowed_per_game": 110}]},
        ]

        game_info = {
            "sport": "basketball_nba",
            "home_team": "Warriors",
            "away_team": "Pistons",
            "commence_time": "2026-01-25T00:00:00Z",
        }

        result = model.analyze_game_odds("game123", [], game_info)

        assert result.prediction == "Warriors"
        assert "Style" in result.reasoning

    def test_away_team_advantage(self, model, mock_table):
        """Test when away team has advantage"""
        # Mock H2H - away team dominated
        mock_table.query.side_effect = [
            {
                "Items": [
                    {"winner": "Bucks"},
                    {"winner": "Bucks"},
                    {"winner": "Bucks"},
                    {"winner": "Bucks"},
                    {"winner": "Nets"},
                ]
            },
            {"Items": [{"points_per_game": 105, "points_allowed_per_game": 112}]},
            {"Items": [{"points_per_game": 118, "points_allowed_per_game": 106}]},
        ]

        game_info = {
            "sport": "basketball_nba",
            "home_team": "Nets",
            "away_team": "Bucks",
            "commence_time": "2026-01-25T00:00:00Z",
        }

        result = model.analyze_game_odds("game123", [], game_info)

        assert result.prediction == "Bucks"

    def test_no_team_stats(self, model, mock_table):
        """Test graceful handling when team stats unavailable"""
        mock_table.query.side_effect = [
            {"Items": []},  # No H2H
            {"Items": []},  # No home stats
            {"Items": []},  # No away stats
        ]

        game_info = {
            "sport": "basketball_nba",
            "home_team": "Team A",
            "away_team": "Team B",
            "commence_time": "2026-01-25T00:00:00Z",
        }

        result = model.analyze_game_odds("game123", [], game_info)

        # Should still return a result with neutral prediction
        assert result is not None
        assert result.confidence >= 0.3

    def test_prop_analysis_with_opponent_history(self, model, mock_table):
        """Test prop analysis using opponent-specific player stats"""
        # Mock game lookup
        mock_table.get_item.return_value = {
            "Item": {
                "home_team": "Lakers",
                "away_team": "Celtics",
                "commence_time": "2026-01-25T00:00:00Z",
            }
        }

        # Mock player stats vs opponent - averages 28 pts vs Celtics
        mock_table.query.return_value = {
            "Items": [
                {"sk": "2026-01-20#celtics", "stats": {"PTS": 30}},
                {"sk": "2026-01-21#celtics", "stats": {"PTS": 28}},
                {"sk": "2026-01-22#celtics", "stats": {"PTS": 26}},
                {"sk": "2026-01-23#celtics", "stats": {"PTS": 29}},
                {"sk": "2026-01-24#celtics", "stats": {"PTS": 27}},
            ]
        }

        prop_item = {
            "sport": "basketball_nba",
            "player_name": "LeBron James",
            "market_key": "player_points",
            "point": 24.5,
            "event_id": "game123",
            "team": "Lakers",
        }

        result = model.analyze_prop_odds(prop_item)

        assert result is not None
        assert "Over" in result.prediction
        assert result.confidence > 0.5
        assert "Celtics" in result.reasoning

    def test_prop_analysis_no_history(self, model, mock_table):
        """Test prop analysis when no opponent history exists"""
        mock_table.get_item.return_value = {
            "Item": {
                "home_team": "Lakers",
                "away_team": "Celtics",
                "commence_time": "2026-01-25T00:00:00Z",
            }
        }

        # No historical stats
        mock_table.query.return_value = {"Items": []}

        prop_item = {
            "sport": "basketball_nba",
            "description": "LeBron James Points",
            "key": "player_points",
            "point": 24.5,
            "event_id": "game123",
            "team": "Lakers",
        }

        result = model.analyze_prop_odds(prop_item)
        assert result is None

    def test_balanced_matchup(self, model, mock_table):
        """Test when matchup is evenly balanced"""
        # Even H2H record
        mock_table.query.side_effect = [
            {
                "Items": [
                    {"winner": "Team A"},
                    {"winner": "Team B"},
                    {"winner": "Team A"},
                    {"winner": "Team B"},
                ]
            },
            {"Items": [{"points_per_game": 110, "points_allowed_per_game": 108}]},
            {"Items": [{"points_per_game": 109, "points_allowed_per_game": 109}]},
        ]

        game_info = {
            "sport": "basketball_nba",
            "home_team": "Team A",
            "away_team": "Team B",
            "commence_time": "2026-01-25T00:00:00Z",
        }

        result = model.analyze_game_odds("game123", [], game_info)

        # Confidence should be moderate for balanced matchup
        assert 0.3 <= result.confidence <= 0.6
