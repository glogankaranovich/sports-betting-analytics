"""Analyses API tests"""

from unittest.mock import Mock, patch

import pytest

from api.analyses import AnalysesHandler


@pytest.fixture
def handler():
    with patch("api.analyses.boto3"):
        return AnalysesHandler()


def test_route_request_get_analyses(handler):
    """Test routing to get_analyses"""
    with patch.object(handler, "get_analyses", return_value={"statusCode": 200}):
        result = handler.route_request("GET", "/analyses", {"sport": "basketball_nba"}, {}, {})
        assert result["statusCode"] == 200


def test_route_request_not_found(handler):
    """Test 404 routing"""
    result = handler.route_request("POST", "/invalid", {}, {}, {})
    assert result["statusCode"] == 404


def test_get_analyses_missing_params(handler):
    """Test missing required params"""
    result = handler.get_analyses({"sport": "basketball_nba"})
    assert result["statusCode"] == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
