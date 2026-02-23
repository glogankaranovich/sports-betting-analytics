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

# Get environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")


def get_api_url():
    """Get API URL for the current environment"""
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    
    stack_prefix = {"dev": "Dev", "beta": "Beta", "prod": "Prod"}.get(ENVIRONMENT, "Dev")
    stack_name = f"{stack_prefix}-BetCollectorApi"
    
    try:
        response = cf_client.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]
        for output in outputs:
            if output["OutputKey"] in ["BetCollectorApiUrl", "ApiUrl"]:
                return output["OutputValue"].rstrip("/")
    except Exception as e:
        print(f"Warning: Could not get API URL from CloudFormation: {e}")
        return None


def get_cognito_config():
    """Get Cognito configuration for the current environment"""
    cf_client = boto3.client("cloudformation", region_name="us-east-1")
    
    stack_prefix = {"dev": "Dev", "beta": "Beta", "prod": "Prod"}.get(ENVIRONMENT, "Dev")
    stack_name = f"{stack_prefix}-Auth"
    
    try:
        response = cf_client.describe_stacks(StackName=stack_name)
        outputs = response["Stacks"][0]["Outputs"]
        config = {}
        for output in outputs:
            if output["OutputKey"] == "UserPoolId":
                config["user_pool_id"] = output["OutputValue"]
            elif output["OutputKey"] == "UserPoolClientId":
                config["client_id"] = output["OutputValue"]
        return config if config else None
    except Exception as e:
        print(f"Warning: Could not get Cognito config: {e}")
        return None


class TestPlayerPropsIntegration(unittest.TestCase):
    """Integration tests for player props API"""

    @classmethod
    def setUpClass(cls):
        """Set up integration test environment"""
        cls.api_url = get_api_url()
        cls.cognito_config = get_cognito_config()
        cls.token = cls._get_auth_token()

    @classmethod
    def _get_auth_token(cls):
        """Get Cognito authentication token"""
        if not cls.cognito_config:
            return None
            
        try:
            client = boto3.client("cognito-idp", region_name="us-east-1")
            response = client.admin_initiate_auth(
                UserPoolId=cls.cognito_config["user_pool_id"],
                ClientId=cls.cognito_config["client_id"],
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
        if not self.api_url or not self.token:
            self.skipTest(f"API not configured for {ENVIRONMENT} environment")
            
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
