"""More user data API tests"""

from unittest.mock import Mock, patch

import pytest

from api.user_data import UserDataHandler


@pytest.fixture
def handler():
    return UserDataHandler()


def test_list_user_models_missing_user_id(handler):
    """Test list models without user_id"""
    response = handler.list_user_models({})
    assert response["statusCode"] == 400


def test_list_user_models_access_denied(handler):
    """Test list models with access denied"""
    with patch("api.user_data.check_feature_access", return_value={"allowed": False, "error": "Access denied"}):
        response = handler.list_user_models({"user_id": "user123"})
        assert response["statusCode"] == 403


def test_create_user_model_missing_user_id(handler):
    """Test create model without user_id"""
    response = handler.create_user_model({})
    assert response["statusCode"] == 400


def test_create_user_model_access_denied(handler):
    """Test create model with access denied"""
    with patch("api.user_data.check_feature_access", return_value={"allowed": False, "error": "Access denied"}):
        response = handler.create_user_model({"user_id": "user123"})
        assert response["statusCode"] == 403


def test_create_user_model_limit_exceeded(handler):
    """Test create model with limit exceeded"""
    with patch("api.user_data.check_feature_access", return_value={"allowed": True}), \
         patch("api.user_data.UserModel.list_by_user", return_value=[Mock(), Mock()]), \
         patch("api.user_data.check_resource_limit", return_value={"allowed": False, "error": "Limit exceeded"}):
        
        response = handler.create_user_model({"user_id": "user123"})
        assert response["statusCode"] == 403


def test_list_custom_data_missing_user_id(handler):
    """Test list custom data without user_id"""
    response = handler.list_custom_data({})
    assert response["statusCode"] == 400


def test_upload_custom_data_missing_user_id(handler):
    """Test upload custom data without user_id"""
    response = handler.upload_custom_data({})
    assert response["statusCode"] == 400


def test_delete_custom_data_missing_user_id(handler):
    """Test delete custom data without user_id"""
    response = handler.delete_custom_data("dataset123", {})
    assert response["statusCode"] == 400


def test_route_request_unknown_endpoint(handler):
    """Test routing to unknown endpoint"""
    response = handler.route_request("GET", "/unknown", {}, {}, {})
    assert response["statusCode"] == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
