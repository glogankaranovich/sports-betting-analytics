"""Tests for outcome_collector accuracy checking methods"""

import os
from unittest.mock import Mock, patch
import pytest

os.environ["DYNAMODB_TABLE"] = "test-table"

from outcome_collector import OutcomeCollector


@pytest.fixture
def collector():
    with patch("outcome_collector.boto3"), patch("outcome_collector.EloCalculator"):
        return OutcomeCollector("test-table", "test-key")


class TestCheckGameAnalysisAccuracy:
    """Test _check_game_analysis_accuracy method"""

    def test_moneyline_home_win_correct(self, collector):
        """Test moneyline prediction for home team winning"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        result = collector._check_game_analysis_accuracy("Lakers", "home", game)
        assert result is True

    def test_moneyline_home_win_incorrect(self, collector):
        """Test moneyline prediction for home team when away wins"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "105",
            "away_score": "110",
        }
        result = collector._check_game_analysis_accuracy("Lakers", "away", game)
        assert result is False

    def test_moneyline_away_win_correct(self, collector):
        """Test moneyline prediction for away team winning"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "105",
            "away_score": "110",
        }
        result = collector._check_game_analysis_accuracy("Warriors", "away", game)
        assert result is True

    def test_spread_home_covers(self, collector):
        """Test home team covering spread"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        # Lakers -3.5: 110 + (-3.5) = 106.5 > 105
        result = collector._check_game_analysis_accuracy("Lakers -3.5", "home", game)
        assert result is True

    def test_spread_home_doesnt_cover(self, collector):
        """Test home team not covering spread"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        # Lakers -6.5: 110 + (-6.5) = 103.5 < 105
        result = collector._check_game_analysis_accuracy("Lakers -6.5", "home", game)
        assert result is False

    def test_spread_away_covers(self, collector):
        """Test away team covering spread"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        # Warriors +7.5: 105 + 7.5 = 112.5 > 110
        result = collector._check_game_analysis_accuracy("Warriors +7.5", "away", game)
        assert result is True

    def test_spread_away_doesnt_cover(self, collector):
        """Test away team not covering spread"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        # Warriors +3.5: 105 + 3.5 = 108.5 < 110
        result = collector._check_game_analysis_accuracy("Warriors +3.5", "away", game)
        assert result is False

    def test_over_hits(self, collector):
        """Test over prediction hitting"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        # Total: 215 > 210.5
        result = collector._check_game_analysis_accuracy("Over 210.5", "home", game)
        assert result is True

    def test_over_misses(self, collector):
        """Test over prediction missing"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        # Total: 215 < 220.5
        result = collector._check_game_analysis_accuracy("Over 220.5", "home", game)
        assert result is False

    def test_under_hits(self, collector):
        """Test under prediction hitting"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        # Total: 215 < 220.5
        result = collector._check_game_analysis_accuracy("Under 220.5", "home", game)
        assert result is True

    def test_under_misses(self, collector):
        """Test under prediction missing"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        # Total: 215 > 210.5
        result = collector._check_game_analysis_accuracy("Under 210.5", "home", game)
        assert result is False

    def test_invalid_prediction_format(self, collector):
        """Test handling of invalid prediction format"""
        game = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }
        result = collector._check_game_analysis_accuracy("Invalid", "home", game)
        assert result is False


class TestCheckPropAnalysisAccuracy:
    """Test _check_prop_analysis_accuracy method"""

    def test_over_prop_hits(self, collector):
        """Test over prop prediction hitting"""
        collector.table = Mock()
        collector.table.query.return_value = {
            "Items": [
                {
                    "stats": {
                        "PTS": 28.0,
                        "REB": 10.0,
                        "AST": 8.0,
                    }
                }
            ]
        }

        analysis = {
            "market_key": "player_points",
            "player_name": "LeBron James",
            "prediction": "Over 25.5",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is True

    def test_over_prop_misses(self, collector):
        """Test over prop prediction missing"""
        collector.table = Mock()
        collector.table.query.return_value = {
            "Items": [
                {
                    "stats": {
                        "PTS": 22.0,
                        "REB": 10.0,
                        "AST": 8.0,
                    }
                }
            ]
        }

        analysis = {
            "market_key": "player_points",
            "player_name": "LeBron James",
            "prediction": "Over 25.5",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is False

    def test_under_prop_hits(self, collector):
        """Test under prop prediction hitting"""
        collector.table = Mock()
        collector.table.query.return_value = {
            "Items": [
                {
                    "stats": {
                        "AST": 5.0,
                    }
                }
            ]
        }

        analysis = {
            "market_key": "player_assists",
            "player_name": "Stephen Curry",
            "prediction": "Under 6.5",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is True

    def test_under_prop_misses(self, collector):
        """Test under prop prediction missing"""
        collector.table = Mock()
        collector.table.query.return_value = {
            "Items": [
                {
                    "stats": {
                        "AST": 8.0,
                    }
                }
            ]
        }

        analysis = {
            "market_key": "player_assists",
            "player_name": "Stephen Curry",
            "prediction": "Under 6.5",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is False

    def test_rebounds_prop(self, collector):
        """Test rebounds prop"""
        collector.table = Mock()
        collector.table.query.return_value = {
            "Items": [{"stats": {"REB": 12.0}}]
        }

        analysis = {
            "market_key": "player_rebounds",
            "player_name": "Anthony Davis",
            "prediction": "Over 10.5",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is True

    def test_threes_prop(self, collector):
        """Test threes made prop"""
        collector.table = Mock()
        collector.table.query.return_value = {
            "Items": [{"stats": {"3PM": 4.0}}]
        }

        analysis = {
            "market_key": "player_threes",
            "player_name": "Klay Thompson",
            "prediction": "Over 3.5",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is True

    def test_no_stats_found(self, collector):
        """Test when player stats not found"""
        collector.table = Mock()
        collector.table.query.return_value = {"Items": []}

        analysis = {
            "market_key": "player_points",
            "player_name": "Unknown Player",
            "prediction": "Over 25.5",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is False

    def test_missing_stat_field(self, collector):
        """Test when stat field is missing"""
        collector.table = Mock()
        collector.table.query.return_value = {
            "Items": [{"stats": {"PTS": 28.0}}]  # Missing AST
        }

        analysis = {
            "market_key": "player_assists",
            "player_name": "LeBron James",
            "prediction": "Over 7.5",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is False

    def test_invalid_prediction_format(self, collector):
        """Test invalid prediction format"""
        collector.table = Mock()
        collector.table.query.return_value = {
            "Items": [{"stats": {"PTS": 28.0}}]
        }

        analysis = {
            "market_key": "player_points",
            "player_name": "LeBron James",
            "prediction": "Invalid",
        }
        game = {"id": "game123", "sport": "basketball_nba"}

        result = collector._check_prop_analysis_accuracy(analysis, game)
        assert result is False


class TestGetStatValue:
    """Test _get_stat_value method"""

    def test_points_mapping(self, collector):
        """Test points stat mapping"""
        stats = {"PTS": 28.0}
        result = collector._get_stat_value(stats, "points")
        assert result == 28.0

    def test_rebounds_mapping(self, collector):
        """Test rebounds stat mapping"""
        stats = {"REB": 12.0}
        result = collector._get_stat_value(stats, "rebounds")
        assert result == 12.0

    def test_assists_mapping(self, collector):
        """Test assists stat mapping"""
        stats = {"AST": 8.0}
        result = collector._get_stat_value(stats, "assists")
        assert result == 8.0

    def test_threes_mapping(self, collector):
        """Test threes made stat mapping"""
        stats = {"3PM": 5.0}
        result = collector._get_stat_value(stats, "threes")
        assert result == 5.0

    def test_steals_mapping(self, collector):
        """Test steals stat mapping"""
        stats = {"STL": 3.0}
        result = collector._get_stat_value(stats, "steals")
        assert result == 3.0

    def test_blocks_mapping(self, collector):
        """Test blocks stat mapping"""
        stats = {"BLK": 2.0}
        result = collector._get_stat_value(stats, "blocks")
        assert result == 2.0

    def test_turnovers_mapping(self, collector):
        """Test turnovers stat mapping"""
        stats = {"TO": 4.0}
        result = collector._get_stat_value(stats, "turnovers")
        assert result == 4.0

    def test_missing_stat(self, collector):
        """Test missing stat returns None"""
        stats = {"PTS": 28.0}
        result = collector._get_stat_value(stats, "assists")
        assert result is None

    def test_unknown_prop_type(self, collector):
        """Test unknown prop type returns None"""
        stats = {"PTS": 28.0}
        result = collector._get_stat_value(stats, "unknown")
        assert result is None

    def test_invalid_stat_value(self, collector):
        """Test invalid stat value returns None"""
        stats = {"PTS": "invalid"}
        result = collector._get_stat_value(stats, "points")
        assert result is None


class TestVerifyInversePredictions:
    """Test _verify_inverse_predictions method"""

    def test_verify_inverse_game_prediction(self, collector):
        """Test verifying inverse game prediction"""
        collector.table = Mock()
        collector.table.get_item.return_value = {
            "Item": {
                "pk": "ANALYSIS#basketball_nba#fanduel#consensus#game",
                "sk": "consensus#game#INVERSE",
                "analysis_type": "game",
                "prediction": "Warriors +5.5",
                "model": "consensus",
                "sport": "basketball_nba",
            }
        }

        original_items = [
            {
                "pk": "ANALYSIS#basketball_nba#fanduel#consensus#game",
                "sk": "consensus#game#LATEST",
                "analysis_type": "game",
                "prediction": "Lakers -5.5",
            }
        ]

        game = {
            "id": "game123",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "home_score": "110",
            "away_score": "105",
        }

        updates = collector._verify_inverse_predictions(original_items, game)
        assert updates == 1
        assert collector.table.update_item.call_count == 1

    def test_verify_inverse_no_inverse_found(self, collector):
        """Test when no inverse prediction exists"""
        collector.table = Mock()
        collector.table.get_item.return_value = {}  # No Item

        original_items = [
            {
                "pk": "ANALYSIS#basketball_nba#fanduel#consensus#game",
                "sk": "consensus#game#LATEST",
            }
        ]

        game = {"id": "game123", "home_score": "110", "away_score": "105"}

        updates = collector._verify_inverse_predictions(original_items, game)
        assert updates == 0

    def test_verify_inverse_empty_list(self, collector):
        """Test with empty original items list"""
        updates = collector._verify_inverse_predictions([], {})
        assert updates == 0


class TestValidateGameResponse:
    """Test _validate_game_response method"""

    def test_valid_game(self, collector):
        """Test valid game response"""
        game = {
            "id": "game123",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "scores": [
                {"name": "Lakers", "score": "110"},
                {"name": "Warriors", "score": "105"},
            ],
        }
        errors = collector._validate_game_response(game)
        assert errors == []

    def test_missing_id(self, collector):
        """Test missing game id"""
        game = {"home_team": "Lakers", "away_team": "Warriors"}
        errors = collector._validate_game_response(game)
        assert "missing_game_id" in errors

    def test_missing_home_team(self, collector):
        """Test missing home team"""
        game = {"id": "game123", "away_team": "Warriors"}
        errors = collector._validate_game_response(game)
        assert "missing_home_team" in errors

    def test_missing_away_team(self, collector):
        """Test missing away team"""
        game = {"id": "game123", "home_team": "Lakers"}
        errors = collector._validate_game_response(game)
        assert "missing_away_team" in errors

    def test_invalid_scores_array(self, collector):
        """Test invalid scores array"""
        game = {
            "id": "game123",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "scores": [{"name": "Lakers"}],  # Only 1 score
        }
        errors = collector._validate_game_response(game)
        assert "scores_array_length_1" in errors

    def test_missing_score_fields(self, collector):
        """Test missing score fields"""
        game = {
            "id": "game123",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "scores": [
                {"name": "Lakers"},  # Missing score
                {"score": "105"},  # Missing name
            ],
        }
        errors = collector._validate_game_response(game)
        assert len(errors) > 0
