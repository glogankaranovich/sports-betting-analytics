"""
Integration tests for new modular API handlers
Tests the deployed Lambda functions in dev environment
"""
import os
import boto3
import pytest
import requests


@pytest.fixture
def api_url():
    """Get API URL from CloudFormation"""
    environment = os.getenv("ENVIRONMENT", "dev")
    environment_title = environment.title()
    
    cloudformation = boto3.client("cloudformation", region_name="us-east-1")
    api_stack_name = f"{environment_title}-BetCollectorApi"
    
    response = cloudformation.describe_stacks(StackName=api_stack_name)
    
    for output in response["Stacks"][0]["Outputs"]:
        if output["OutputKey"] == "BetCollectorApiUrl":
            return output["OutputValue"].rstrip("/")
    
    raise ValueError("API URL not found in stack outputs")


class TestGamesHandler:
    """Test games handler endpoints"""

    def test_health_endpoint(self, api_url):
        """Test health endpoint (public, no auth)"""
        response = requests.get(f"{api_url}/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "environment" in data
        print(f"✓ Health check passed: {data}")

    def test_games_endpoint_requires_sport(self, api_url):
        """Test games endpoint requires sport parameter"""
        response = requests.get(f"{api_url}/games")
        
        assert response.status_code in [400, 401]
        print(f"✓ Games validation working (status: {response.status_code})")

    def test_sports_endpoint(self, api_url):
        """Test sports endpoint"""
        response = requests.get(f"{api_url}/sports")
        
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "sports" in data
            print(f"✓ Sports endpoint: {data.get('count', 0)} sports found")

    def test_bookmakers_endpoint(self, api_url):
        """Test bookmakers endpoint"""
        response = requests.get(f"{api_url}/bookmakers")
        
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "bookmakers" in data
            print(f"✓ Bookmakers endpoint: {len(data.get('bookmakers', []))} bookmakers found")


class TestAnalysesHandler:
    """Test analyses handler endpoints"""

    def test_analyses_endpoint_requires_params(self, api_url):
        """Test analyses endpoint requires bookmaker and model"""
        response = requests.get(f"{api_url}/analyses?sport=basketball_nba")
        
        assert response.status_code in [400, 401]
        print(f"✓ Analyses validation working (status: {response.status_code})")

    def test_top_analysis_endpoint(self, api_url):
        """Test top analysis endpoint"""
        response = requests.get(f"{api_url}/top-analysis?sport=basketball_nba&bookmaker=fanduel")
        
        assert response.status_code in [200, 401]
        
        if response.status_code == 200:
            data = response.json()
            assert "sport" in data
            assert "bookmaker" in data
            print(f"✓ Top analysis endpoint working")


class TestMiscHandler:
    """Test misc handler endpoints"""

    def test_benny_dashboard_endpoint(self, api_url):
        """Test benny dashboard endpoint (public)"""
        response = requests.get(f"{api_url}/benny/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        print(f"✓ Benny dashboard: {data}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

