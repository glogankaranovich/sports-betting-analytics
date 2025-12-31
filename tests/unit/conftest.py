"""
Shared test fixtures and configuration
"""
import pytest
import asyncio
from unittest.mock import Mock


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_aws_credentials():
    """Mock AWS credentials for testing"""
    return {
        "aws_access_key_id": "test_key",
        "aws_secret_access_key": "test_secret",
        "region_name": "us-east-1"
    }


@pytest.fixture
def mock_api_response():
    """Mock API response for testing"""
    return {
        "status": "success",
        "data": [
            {"id": 1, "name": "Test Item 1"},
            {"id": 2, "name": "Test Item 2"}
        ]
    }


@pytest.fixture
def sample_sports_event():
    """Sample sports event data for testing"""
    return {
        "sport": "americanfootball_nfl",
        "home_team": "Los Angeles Rams",
        "away_team": "San Francisco 49ers",
        "commence_time": "2024-01-15T18:00:00Z",
        "bookmaker_odds": [
            {
                "bookmaker": "draftkings",
                "market": "h2h",
                "outcomes": [
                    {"name": "Los Angeles Rams", "price": 1.85},
                    {"name": "San Francisco 49ers", "price": 1.95}
                ]
            }
        ]
    }
