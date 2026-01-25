"""
Unit tests for Injury Collector
"""

import pytest
from unittest.mock import Mock, patch
from injury_collector import InjuryCollector, lambda_handler


@pytest.fixture
def mock_dynamodb():
    with patch("injury_collector.boto3") as mock_boto3:
        mock_table = Mock()
        mock_resource = Mock()
        mock_resource.Table.return_value = mock_table
        mock_boto3.resource.return_value = mock_resource
        yield mock_table


@pytest.fixture
def collector(mock_dynamodb):
    with patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"}):
        return InjuryCollector()


def test_parse_injury(collector):
    """Test parsing injury data from ESPN API"""

    injury_data = {
        "id": "514486",
        "status": "Out",
        "shortComment": "Player is out with knee injury",
        "longComment": "Player will miss 2-3 weeks",
        "date": "2026-01-19T15:38Z",
        "athlete": {"$ref": "http://api.espn.com/athletes/12345?lang=en"},
        "details": {
            "type": "Knee",
            "location": "Leg",
            "detail": "Bruise",
            "side": "Left",
            "returnDate": "2026-01-26",
        },
    }

    result = collector._parse_injury(injury_data)

    assert result["injury_id"] == "514486"
    assert result["athlete_id"] == "12345"
    assert result["status"] == "Out"
    assert result["injury_type"] == "Knee"
    assert result["location"] == "Leg"
    assert result["detail"] == "Bruise"
    assert result["side"] == "Left"
    assert result["return_date"] == "2026-01-26"


def test_parse_injury_missing_details(collector):
    """Test parsing injury with missing details"""

    injury_data = {
        "id": "123",
        "status": "Questionable",
        "athlete": {"$ref": "http://api.espn.com/athletes/999?lang=en"},
    }

    result = collector._parse_injury(injury_data)

    assert result["injury_id"] == "123"
    assert result["athlete_id"] == "999"
    assert result["status"] == "Questionable"
    assert result["injury_type"] is None


@patch("injury_collector.requests.get")
def test_fetch_team_injuries(mock_get, collector):
    """Test fetching team injuries"""
    mock_response = Mock()
    mock_response.json.side_effect = [
        {"items": [{"$ref": "http://api.espn.com/injury/1"}]},
        {
            "id": "1",
            "status": "Out",
            "athlete": {"$ref": "http://api.espn.com/athletes/123"},
            "details": {},
        },
    ]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    injuries = collector._fetch_team_injuries("basketball", "nba", "1")

    assert len(injuries) == 1
    assert injuries[0]["injury_id"] == "1"


@patch("injury_collector.requests.get")
def test_fetch_team_injuries_error(mock_get, collector):
    """Test handling errors when fetching injuries"""
    mock_get.side_effect = Exception("API error")

    injuries = collector._fetch_team_injuries("basketball", "nba", "1")

    assert injuries == []


def test_store_injuries(mock_dynamodb, collector):
    """Test storing injuries in DynamoDB"""
    injuries = [
        {"injury_id": "1", "status": "Out", "athlete_id": "123"},
        {"injury_id": "2", "status": "Questionable", "athlete_id": "456"},
    ]

    collector._store_injuries("basketball_nba", "1", "Atlanta Hawks", injuries)

    mock_dynamodb.put_item.assert_called_once()
    call_args = mock_dynamodb.put_item.call_args[1]
    item = call_args["Item"]

    assert item["pk"] == "INJURIES#basketball_nba#1"
    assert item["sport"] == "basketball_nba"
    assert item["team_id"] == "1"
    assert item["team_name"] == "Atlanta Hawks"
    assert item["injury_count"] == 2
    assert len(item["injuries"]) == 2


@patch("injury_collector.requests.get")
def test_get_teams(mock_get, collector):
    """Test getting teams for a sport"""
    mock_response = Mock()
    mock_response.json.side_effect = [
        {"items": [{"$ref": "http://api.espn.com/teams/1"}]},
        {"id": "1", "displayName": "Atlanta Hawks"},
    ]
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response

    teams = collector._get_teams("basketball", "nba")

    assert len(teams) == 1
    assert teams[0]["id"] == "1"
    assert teams[0]["name"] == "Atlanta Hawks"


@patch.object(InjuryCollector, "_get_teams")
@patch.object(InjuryCollector, "_fetch_team_injuries")
@patch.object(InjuryCollector, "_store_injuries")
def test_collect_injuries_for_sport(mock_store, mock_fetch, mock_get_teams, collector):
    """Test collecting injuries for a sport"""
    mock_get_teams.return_value = [
        {"id": "1", "name": "Team A"},
        {"id": "2", "name": "Team B"},
    ]
    mock_fetch.side_effect = [
        [{"injury_id": "1"}],
        [{"injury_id": "2"}, {"injury_id": "3"}],
    ]

    count = collector.collect_injuries_for_sport("basketball_nba")

    assert count == 3
    assert mock_store.call_count == 2


def test_collect_injuries_unsupported_sport(collector):
    """Test collecting injuries for unsupported sport"""
    count = collector.collect_injuries_for_sport("unsupported_sport")
    assert count == 0


@patch.object(InjuryCollector, "collect_injuries_for_sport")
@patch.dict("os.environ", {"DYNAMODB_TABLE": "test-table"})
def test_lambda_handler(mock_collect):
    """Test Lambda handler"""
    mock_collect.return_value = 5

    event = {"sport": "basketball_nba"}
    result = lambda_handler(event, None)

    assert result["statusCode"] == 200
    assert result["body"]["injuries_collected"] == 5
    assert result["body"]["sport"] == "basketball_nba"
