#!/usr/bin/env python3
"""
Integration tests for player props functionality
"""

import json
import os
import unittest
from decimal import Decimal

import boto3
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
