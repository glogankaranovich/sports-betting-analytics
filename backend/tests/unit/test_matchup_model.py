"""
Unit tests for Matchup Model
"""

import pytest
from unittest.mock import MagicMock
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
        mock_table.scan.return_value = {
            "Items": [
                {"winner": "Lakers", "home_team": "Lakers"},
                {"winner": "Lakers", "home_team": "Lakers"},
                {"winner": "Lakers", "away_team": "Lakers"},
                {"winner": "Lakers", "home_team": "Lakers"},
                {"winner": "Celtics", "away_team": "Celtics"},
                {"winner": "Lakers", "home_team": "Lakers"},
                {"winner": "Lakers", "away_team": "Lakers"},
                {"winner": "Celtics", "home_team": "Celtics"},
                {"winner": "Lakers", "home_team": "Lakers"},
                {"winner": "Lakers", "away_team": "Lakers"},
            ]
        }

        # Mock team stats
        mock_table.query.side_effect = [
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
        mock_table.scan.return_value = {"Items": []}
        mock_table.query.side_effect = [
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
        mock_table.scan.return_value = {"Items": []}

        # Home team: high offense (125), good defense (95)
        # Away team: low offense (90), poor defense (110)
        # offense: 125 - 110 = +15, defense: 90 - 95 = -5, total = 10/20 = 0.5
        mock_table.query.side_effect = [
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
        mock_table.scan.return_value = {
            "Items": [
                {"winner": "Bucks", "away_team": "Bucks"},
                {"winner": "Bucks", "home_team": "Bucks"},
                {"winner": "Bucks", "away_team": "Bucks"},
                {"winner": "Bucks", "away_team": "Bucks"},
                {"winner": "Nets", "home_team": "Nets"},
            ]
        }

        mock_table.query.side_effect = [
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
        mock_table.scan.return_value = {"Items": []}
        mock_table.query.side_effect = [{"Items": []}, {"Items": []}]

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

    def test_prop_analysis_not_implemented(self, model):
        """Test that prop analysis returns None (requires opponent-specific data)"""
        prop_item = {
            "sport": "basketball_nba",
            "player_name": "LeBron James",
            "prop_type": "points",
        }

        result = model.analyze_prop_odds(prop_item)
        assert result is None

    def test_balanced_matchup(self, model, mock_table):
        """Test when matchup is evenly balanced"""
        # Even H2H record
        mock_table.scan.return_value = {
            "Items": [
                {"winner": "Team A"},
                {"winner": "Team B"},
                {"winner": "Team A"},
                {"winner": "Team B"},
            ]
        }

        # Similar team stats
        mock_table.query.side_effect = [
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
