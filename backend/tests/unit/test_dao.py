"""
Unit tests for dao module
"""
from unittest.mock import MagicMock, patch

import pytest

from dao import BettingDAO


@pytest.fixture
def dao():
    """Create DAO instance with mocked DynamoDB"""
    with patch("dao.boto3") as mock_boto3:
        mock_table = MagicMock()
        mock_resource = MagicMock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_resource

        dao_instance = BettingDAO()
        dao_instance.table = mock_table
        yield dao_instance


class TestGetGameIdsFromDb:
    """Test get_game_ids_from_db method"""

    def test_get_game_ids_success(self, dao):
        dao.table.query.return_value = {
            "Items": [
                {"pk": "GAME#game123"},
                {"pk": "GAME#game456"},
                {"pk": "GAME#game123"},  # Duplicate
            ]
        }

        game_ids = dao.get_game_ids_from_db("nba")

        assert len(game_ids) == 2
        assert "game123" in game_ids
        assert "game456" in game_ids

        # Verify query parameters
        call_args = dao.table.query.call_args[1]
        assert call_args["IndexName"] == "ActiveBetsIndexV2"
        assert ":active_bet_pk" in call_args["ExpressionAttributeValues"]
        assert call_args["ExpressionAttributeValues"][":active_bet_pk"] == "GAME#nba"

    def test_get_game_ids_pagination(self, dao):
        dao.table.query.side_effect = [
            {"Items": [{"pk": "GAME#game1"}], "LastEvaluatedKey": {"pk": "GAME#game1"}},
            {
                "Items": [{"pk": "GAME#game2"}],
            },
        ]

        game_ids = dao.get_game_ids_from_db("nfl")

        assert len(game_ids) == 2
        assert dao.table.query.call_count == 2

    def test_get_game_ids_error(self, dao):
        dao.table.query.side_effect = Exception("DynamoDB error")

        game_ids = dao.get_game_ids_from_db("nba")

        assert game_ids == []


class TestGetPropIdsFromDb:
    """Test get_prop_ids_from_db method"""

    def test_get_prop_ids_success(self, dao):
        dao.table.query.return_value = {
            "Items": [
                {"pk": "PROP#event123#LeBron James"},
                {"pk": "PROP#event456#Stephen Curry"},
            ]
        }

        prop_ids = dao.get_prop_ids_from_db("nba")

        assert len(prop_ids) == 2
        assert "event123#LeBron James" in prop_ids
        assert "event456#Stephen Curry" in prop_ids

    def test_get_prop_ids_invalid_format(self, dao):
        dao.table.query.return_value = {
            "Items": [
                {"pk": "PROP#invalid"},  # Missing player name
                {"pk": "PROP#event123#Player"},
            ]
        }

        prop_ids = dao.get_prop_ids_from_db("nba")

        assert len(prop_ids) == 1
        assert "event123#Player" in prop_ids

    def test_get_prop_ids_error(self, dao):
        dao.table.query.side_effect = Exception("DynamoDB error")

        prop_ids = dao.get_prop_ids_from_db("nba")

        assert prop_ids == []


class TestGetPropData:
    """Test get_prop_data method"""

    def test_get_prop_data_success(self, dao):
        dao.table.query.return_value = {
            "Items": [
                {
                    "player_name": "LeBron James",
                    "market_key": "player_points",
                    "event_id": "event123",
                    "sport": "nba",
                    "commence_time": "2026-02-08T19:00:00Z",
                    "bookmaker": "fanduel",
                    "outcome": "Over",
                    "point": 25.5,
                    "price": -110,
                }
            ]
        }

        prop_data = dao.get_prop_data("event123#LeBron James")

        assert len(prop_data) == 1
        assert prop_data[0]["player_name"] == "LeBron James"
        assert prop_data[0]["point"] == 25.5

    def test_get_prop_data_error(self, dao):
        dao.table.query.side_effect = Exception("DynamoDB error")

        prop_data = dao.get_prop_data("event123#Player")

        assert prop_data == []


class TestGetGameBetRecords:
    """Test get_game_bet_records method"""

    def test_get_game_bet_records_success(self, dao):
        dao.table.query.return_value = {
            "Items": [
                {"pk": "GAME#game123", "sk": "fanduel#h2h", "latest": True},
                {"pk": "GAME#game123", "sk": "draftkings#h2h", "latest": True},
            ]
        }

        records = dao.get_game_bet_records("game123")

        assert len(records) == 2
        assert records[0]["pk"] == "GAME#game123"

    def test_get_game_bet_records_error(self, dao):
        dao.table.query.side_effect = Exception("DynamoDB error")

        records = dao.get_game_bet_records("game123")

        assert records == []


class TestGetGameData:
    """Test get_game_data method"""

    def test_get_game_data_success(self, dao):
        dao.table.query.return_value = {
            "Items": [
                {
                    "pk": "GAME#game123",
                    "sk": "fanduel#h2h",
                    "sport": "nba",
                    "home_team": "Lakers",
                    "away_team": "Celtics",
                    "commence_time": "2026-02-08T19:00:00Z",
                    "outcomes": [{"name": "Lakers", "price": -110}],
                },
                {
                    "pk": "GAME#game123",
                    "sk": "draftkings#h2h",
                    "sport": "nba",
                    "home_team": "Lakers",
                    "away_team": "Celtics",
                    "commence_time": "2026-02-08T19:00:00Z",
                    "outcomes": [{"name": "Lakers", "price": -115}],
                },
            ]
        }

        game_data = dao.get_game_data("game123")

        assert game_data is not None
        assert game_data["game_id"] == "game123"
        assert game_data["home_team"] == "Lakers"
        assert game_data["away_team"] == "Celtics"
        assert len(game_data["bookmakers"]) == 2

    def test_get_game_data_not_found(self, dao):
        dao.table.query.return_value = {"Items": []}

        game_data = dao.get_game_data("nonexistent")

        assert game_data is None

    def test_get_game_data_error(self, dao):
        dao.table.query.side_effect = Exception("DynamoDB error")

        game_data = dao.get_game_data("game123")

        assert game_data is None


class TestGetGameAnalysis:
    """Test get_game_analysis method"""

    def test_get_game_analysis_success(self, dao):
        dao.table.query.return_value = {
            "Items": [
                {
                    "pk": "ANALYSIS#game123",
                    "sk": "consensus",
                    "game_id": "game123",
                    "sport": "nba",
                    "home_team": "Lakers",
                    "away_team": "Celtics",
                    "commence_time": "2026-02-08T19:00:00Z",
                    "home_win_probability": 0.55,
                    "away_win_probability": 0.45,
                    "confidence_score": 0.75,
                    "model": "consensus",
                    "status": "active",
                    "value_bets": [],
                }
            ]
        }

        result = dao.get_game_analysis("nba")

        assert len(result["items"]) == 1
        assert result["items"][0]["game_id"] == "game123"
        assert result["items"][0]["home_win_probability"] == 0.55

    def test_get_game_analysis_with_pagination(self, dao):
        dao.table.query.return_value = {
            "Items": [{"pk": "ANALYSIS#game123"}],
            "LastEvaluatedKey": {"pk": "ANALYSIS#game123"},
        }

        result = dao.get_game_analysis(
            "nba", limit=10, last_evaluated_key={"pk": "prev"}
        )

        assert result["lastEvaluatedKey"] is not None
        call_args = dao.table.query.call_args[1]
        assert call_args["Limit"] == 10
        assert "ExclusiveStartKey" in call_args

    def test_get_game_analysis_error(self, dao):
        dao.table.query.side_effect = Exception("DynamoDB error")

        result = dao.get_game_analysis("nba")

        assert result["items"] == []
        assert result["lastEvaluatedKey"] is None


class TestGetPropAnalysis:
    """Test get_prop_analysis method"""

    def test_get_prop_analysis_success(self, dao):
        dao.table.query.return_value = {
            "Items": [
                {
                    "pk": "ANALYSIS#prop123",
                    "sk": "consensus",
                    "event_id": "event123",
                    "player_name": "LeBron James",
                    "prop_type": "points",
                    "sport": "nba",
                    "commence_time": "2026-02-08T19:00:00Z",
                    "predicted_value": 26.5,
                    "over_probability": 0.52,
                    "under_probability": 0.48,
                    "confidence_score": 0.65,
                    "model": "consensus",
                }
            ]
        }

        result = dao.get_prop_analysis("nba")

        assert len(result["items"]) == 1
        assert result["items"][0]["player_name"] == "LeBron James"
        assert result["items"][0]["predicted_value"] == 26.5

    def test_get_prop_analysis_error(self, dao):
        dao.table.query.side_effect = Exception("DynamoDB error")

        result = dao.get_prop_analysis("nba")

        assert result["items"] == []
        assert result["lastEvaluatedKey"] is None
