"""
Tests for outcome collector - historical odds archiving
"""
import unittest
from unittest.mock import MagicMock

from outcome_collector import OutcomeCollector


class TestOutcomeCollectorArchiving(unittest.TestCase):
    def setUp(self):
        self.collector = OutcomeCollector("test-table", "test-api-key")
        self.collector.table = MagicMock()

    def test_archive_game_odds_success(self):
        """Test successful archiving of game odds"""
        game = {"id": "test_game_123"}

        # Mock odds records
        self.collector.table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#test_game_123",
                    "sk": "draftkings#h2h#LATEST",
                    "active_bet_pk": "ACTIVE#123",
                    "bookmaker": "draftkings",
                    "outcomes": [{"name": "Team A", "price": -110}],
                },
                {
                    "pk": "GAME#test_game_123",
                    "sk": "fanduel#h2h#LATEST",
                    "bookmaker": "fanduel",
                    "outcomes": [{"name": "Team B", "price": 100}],
                },
            ]
        }

        self.collector._archive_game_odds(game)

        # Verify put_item called twice (once per odds record)
        assert self.collector.table.put_item.call_count == 2

        # Verify archived records have correct structure
        first_call = self.collector.table.put_item.call_args_list[0][1]["Item"]
        assert first_call["pk"] == "HISTORICAL_ODDS#test_game_123"
        assert first_call["sk"] == "draftkings#h2h"
        assert "active_bet_pk" not in first_call
        assert "archived_at" in first_call

    def test_archive_game_odds_skips_non_latest(self):
        """Test that non-LATEST records are not archived"""
        game = {"id": "test_game_123"}

        self.collector.table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#test_game_123",
                    "sk": "draftkings#h2h#2024-01-01T12:00:00",
                    "bookmaker": "draftkings",
                }
            ]
        }

        self.collector._archive_game_odds(game)

        # Should not archive historical snapshots
        self.collector.table.put_item.assert_not_called()

    def test_archive_game_odds_handles_missing_game_id(self):
        """Test graceful handling of missing game ID"""
        game = {}

        self.collector._archive_game_odds(game)

        # Should return early without querying
        self.collector.table.query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
