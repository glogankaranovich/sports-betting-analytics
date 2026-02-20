import json
import os
import sys
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

# Mock environment before importing
os.environ["DYNAMODB_TABLE"] = "test-table"

sys.path.append(".")  # Add current directory to path for local imports
from api_handler import lambda_handler  # noqa: E402
from api.utils import create_response, decimal_to_float  # noqa: E402

"""
API Handler Tests - Profile/Subscription endpoints only
Other endpoints have been migrated to modular handlers
"""


class TestApiHandler(unittest.TestCase):
    def setUp(self):
        """Set up test environment"""
        os.environ["DYNAMODB_TABLE"] = "test-table"
        os.environ["ENVIRONMENT"] = "test"

    def test_decimal_to_float_conversion(self):
        """Test decimal to float conversion utility"""
        data = {
            "price": Decimal("100.50"),
            "nested": {"value": Decimal("25.75"), "string": "test"},
            "list": [Decimal("1.5"), "text", Decimal("2.5")],
        }

        result = decimal_to_float(data)

        self.assertEqual(result["price"], 100.5)
        self.assertEqual(result["nested"]["value"], 25.75)
        self.assertEqual(result["nested"]["string"], "test")
        self.assertEqual(result["list"][0], 1.5)
        self.assertEqual(result["list"][1], "text")
        self.assertEqual(result["list"][2], 2.5)

    def test_create_response(self):
        """Test response creation utility"""
        response = create_response(200, {"message": "success"})
        
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", response["headers"])
        body = json.loads(response["body"])
        self.assertEqual(body["message"], "success")

    def test_cors_preflight(self):
        """Test CORS preflight request"""
        event = {"httpMethod": "OPTIONS", "path": "/profile", "queryStringParameters": None}
        response = lambda_handler(event, {})
        
        self.assertEqual(response["statusCode"], 200)

    @patch("api.user.table")
    def test_profile_endpoint(self, mock_table):
        """Test profile GET endpoint"""
        mock_table.get_item.return_value = {
            "Item": {
                "pk": "USER#test-user",
                "sk": "PROFILE",
                "user_id": "test-user",
                "email": "test@example.com",
                "subscription_tier": "free"
            }
        }

        event = {
            "httpMethod": "GET",
            "path": "/profile",
            "queryStringParameters": {"user_id": "test-user"}
        }

        response = lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

    def test_unknown_endpoint(self):
        """Test unknown endpoint returns 404"""
        event = {
            "httpMethod": "GET",
            "path": "/unknown",
            "queryStringParameters": None
        }

        response = lambda_handler(event, {})
        self.assertEqual(response["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
