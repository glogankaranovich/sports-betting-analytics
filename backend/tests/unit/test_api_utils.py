"""More API utils tests"""

from decimal import Decimal
from unittest.mock import Mock, patch

import pytest

from api.utils import BaseAPIHandler, decimal_to_float


def test_base_api_handler_success_response():
    """Test success response"""
    handler = BaseAPIHandler()
    
    response = handler.success_response({"data": "test"})
    assert response["statusCode"] == 200
    assert "data" in response["body"]


def test_base_api_handler_error_response():
    """Test error response"""
    handler = BaseAPIHandler()
    
    response = handler.error_response("Error message", 400)
    assert response["statusCode"] == 400


def test_decimal_to_float_nested():
    """Test decimal to float with nested structures"""
    obj = {
        "value": Decimal("1.5"),
        "list": [Decimal("2.5"), Decimal("3.5")],
        "nested": {"val": Decimal("4.5")}
    }
    
    result = decimal_to_float(obj)
    assert isinstance(result["value"], float)
    assert isinstance(result["list"][0], float)
    assert isinstance(result["nested"]["val"], float)


def test_decimal_to_float_non_decimal():
    """Test decimal to float with non-decimal values"""
    obj = {"string": "test", "int": 42, "bool": True}
    
    result = decimal_to_float(obj)
    assert result["string"] == "test"
    assert result["int"] == 42
    assert result["bool"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
