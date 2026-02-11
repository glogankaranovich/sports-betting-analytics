"""
Tests for odds cleanup Lambda
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import odds_cleanup


class TestOddsCleanup(unittest.TestCase):
    @patch("odds_cleanup.bets_table")
    def test_cleanup_deletes_stale_odds(self, mock_table):
        """Test cleanup deletes odds for uncompleted games >7 days old"""

        # Mock stale game without outcome
        mock_table.scan.return_value = {
            "Items": [
                {
                    "pk": "GAME#old_game_123",
                    "sk": "draftkings#h2h#LATEST",
                    "commence_time": (
                        datetime.utcnow() - timedelta(days=10)
                    ).isoformat(),
                }
            ]
        }

        # No outcome exists
        mock_table.query.return_value = {"Items": []}

        result = odds_cleanup.handler({}, {})

        # Should delete the stale record
        mock_table.delete_item.assert_called_once()
        assert result["statusCode"] == 200
        assert result["deleted_count"] == 1

    @patch("odds_cleanup.bets_table")
    def test_cleanup_skips_completed_games(self, mock_table):
        """Test cleanup skips games that have outcomes"""

        # Mock old game
        mock_table.scan.return_value = {
            "Items": [
                {
                    "pk": "GAME#completed_game_123",
                    "sk": "draftkings#h2h#LATEST",
                    "commence_time": (
                        datetime.utcnow() - timedelta(days=10)
                    ).isoformat(),
                }
            ]
        }

        # Outcome exists (game completed)
        mock_table.query.return_value = {
            "Items": [{"pk": "OUTCOME#completed_game_123"}]
        }

        result = odds_cleanup.handler({}, {})

        # Should NOT delete
        mock_table.delete_item.assert_not_called()
        assert result["deleted_count"] == 0

    @patch("odds_cleanup.bets_table")
    def test_cleanup_handles_no_stale_games(self, mock_table):
        """Test cleanup handles case with no stale games"""
        mock_table.scan.return_value = {"Items": []}

        result = odds_cleanup.handler({}, {})

        assert result["statusCode"] == 200
        assert result["deleted_count"] == 0
        mock_table.delete_item.assert_not_called()


if __name__ == "__main__":
    unittest.main()
