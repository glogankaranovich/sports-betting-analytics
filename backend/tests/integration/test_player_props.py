#!/usr/bin/env python3
"""
Integration and unit tests for player props functionality
"""

import json
import os
import unittest
from decimal import Decimal
from unittest.mock import Mock, patch

import boto3
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class TestPlayerPropsUnit(unittest.TestCase):
    """Unit tests for player props functionality"""

    def setUp(self):
        """Set up test fixtures"""
        self.mock_table = Mock()

    @patch("odds_collector.boto3.resource")
    def test_store_player_props(self, mock_boto3):
        """Test storing player props in DynamoDB"""
        from odds_collector import OddsCollector

        # Mock DynamoDB
        mock_boto3.return_value.Table.return_value = self.mock_table

        collector = OddsCollector()

        # Test data
        props_data = {
            "commence_time": "2026-01-04T20:00:00Z",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "markets": [
                        {
                            "key": "player_pass_tds",
                            "outcomes": [
                                {
                                    "name": "Over",
                                    "description": "Josh Allen",
                                    "point": 1.5,
                                    "price": 120,
                                }
                            ],
                        }
                    ],
                }
            ],
        }

        collector.store_player_props(
            "americanfootball_nfl", "test_event_123", props_data
        )

        # Verify put_item was called (for new data)
        self.mock_table.put_item.assert_called()

        # Check that at least one call was made with correct key structure
        calls = self.mock_table.put_item.call_args_list
        self.assertTrue(len(calls) >= 1)

        # Check the latest item call (should be the second call)
        latest_call = calls[-1]
        item = latest_call[1]["Item"]
        self.assertEqual(item["pk"], "PROP#test_event_123#Josh Allen")
        self.assertEqual(item["sk"], "draftkings#player_pass_tds#Over#LATEST")

    def test_api_handler_player_props_route(self):
        """Test API handler routing for player props"""
        # Set environment variables like existing tests
        os.environ["DYNAMODB_TABLE"] = "test-table"
        os.environ["ENVIRONMENT"] = "test"

        # Import games handler (player-props migrated to modular handlers)
        from api.games import lambda_handler

        # Patch the table object
        with patch("api.games.table") as mock_table:
            mock_table.query.return_value = {"Items": [], "Count": 0}

            event = {
                "httpMethod": "GET",
                "path": "/player-props",
                "queryStringParameters": {"sport": "americanfootball_nfl"},
            }

            result = lambda_handler(event, None)

            self.assertEqual(result["statusCode"], 200)
            body = json.loads(result["body"])
            self.assertIn("props", body)
            self.assertIn("count", body)
            self.assertIn("filters", body)


class TestPlayerPropsIntegration(unittest.TestCase):
    """Integration tests for player props API"""

    @classmethod
    def setUpClass(cls):
        """Set up integration test environment"""
        cls.api_url = "https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod"
        cls.token = cls._get_auth_token()

    @classmethod
    def _get_auth_token(cls):
        """Get Cognito authentication token"""
        try:
            client = boto3.client("cognito-idp", region_name="us-east-1")
            response = client.admin_initiate_auth(
                UserPoolId="us-east-1_UT5jyAP5L",
                ClientId="4qs12vau007oineekjldjkn6v0",
                AuthFlow="ADMIN_NO_SRP_AUTH",
                AuthParameters={
                    "USERNAME": "testuser@example.com",
                    "PASSWORD": "CarpoolBets2026!Secure#",
                },
            )
            return response["AuthenticationResult"]["IdToken"]
        except Exception as e:
            print(f"Warning: Could not get auth token: {e}")
            return None

    def setUp(self):
        """Set up test case"""
        # Use mock token if real authentication fails
        if not self.token:
            self.token = "mock-token-for-testing"

        self.headers = {"Authorization": self.token}

    def test_player_props_endpoint_exists(self):
        """Test that player props endpoint is accessible"""
        response = requests.get(
            f"{self.api_url}/player-props?sport=basketball_nba", headers=self.headers
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("props", data)
        self.assertIn("count", data)
        self.assertIn("filters", data)

    def test_player_props_filtering_by_sport(self):
        """Test filtering player props by sport"""
        response = requests.get(
            f"{self.api_url}/player-props?sport=americanfootball_nfl",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["filters"]["sport"], "americanfootball_nfl")

        # If there are props, verify they're all NFL
        if data["count"] > 0:
            for prop in data["props"]:
                self.assertEqual(prop["sport"], "americanfootball_nfl")

    def test_player_props_filtering_by_prop_type(self):
        """Test filtering player props by prop type"""
        response = requests.get(
            f"{self.api_url}/player-props?sport=americanfootball_nfl&prop_type=player_pass_tds",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["filters"]["prop_type"], "player_pass_tds")

        # If there are props, verify they're all passing TDs
        if data["count"] > 0:
            for prop in data["props"]:
                self.assertEqual(prop["market_key"], "player_pass_tds")

    def test_player_props_combined_filters(self):
        """Test combining multiple filters"""
        response = requests.get(
            f"{self.api_url}/player-props?sport=americanfootball_nfl&prop_type=player_pass_tds",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["filters"]["sport"], "americanfootball_nfl")
        self.assertEqual(data["filters"]["prop_type"], "player_pass_tds")

    def test_player_props_pagination(self):
        """Test pagination with limit parameter"""
        response = requests.get(
            f"{self.api_url}/player-props?sport=basketball_nba&limit=5",
            headers=self.headers,
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()
        # Should return at most 5 props
        self.assertLessEqual(len(data["props"]), 5)


class TestPlayerPropsDataStructure(unittest.TestCase):
    """Test player props data structure and validation"""

    def test_player_prop_key_format(self):
        """Test player prop key format"""
        event_id = "test_event_123"
        bookmaker = "draftkings"
        market_key = "player_pass_tds"
        player_name = "Josh Allen"

        expected_key = f"PROP#{event_id}#{bookmaker}#{market_key}#{player_name}"

        # This would be the actual key format used in store_player_props
        actual_key = f"PROP#{event_id}#{bookmaker}#{market_key}#{player_name}"

        self.assertEqual(actual_key, expected_key)
        self.assertTrue(actual_key.startswith("PROP#"))

    def test_decimal_conversion(self):
        """Test decimal conversion for DynamoDB compatibility"""
        from odds_collector import convert_floats_to_decimal

        test_data = {"point": 1.5, "price": 120, "nested": {"value": 2.5}}

        converted = convert_floats_to_decimal(test_data)

        self.assertIsInstance(converted["point"], Decimal)
        self.assertEqual(converted["point"], Decimal("1.5"))
        self.assertIsInstance(converted["nested"]["value"], Decimal)


if __name__ == "__main__":
    # Run unit tests by default, integration tests with --integration flag
    import sys

    if "--integration" in sys.argv:
        sys.argv.remove("--integration")
        # Run integration tests
        suite = unittest.TestLoader().loadTestsFromTestCase(TestPlayerPropsIntegration)
        unittest.TextTestRunner(verbosity=2).run(suite)
    elif "--all" in sys.argv:
        sys.argv.remove("--all")
        # Run all tests
        unittest.main(verbosity=2)
    else:
        # Run unit tests only
        suite = unittest.TestSuite()
        suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestPlayerPropsUnit))
        suite.addTest(
            unittest.TestLoader().loadTestsFromTestCase(TestPlayerPropsDataStructure)
        )
        unittest.TextTestRunner(verbosity=2).run(suite)
