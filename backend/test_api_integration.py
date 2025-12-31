import requests
import json
import os
import boto3
from typing import Dict, Any

def test_api_integration():
    """Integration test to verify API endpoints work with real AWS resources"""
    
    # Get environment-specific resources
    environment = os.getenv('ENVIRONMENT', 'dev')
    
    # Get API URL from CloudFormation stack outputs
    cloudformation = boto3.client('cloudformation', region_name='us-east-1')
    
    try:
        # Get the API URL from stack outputs
        stack_name = f'CarpoolBetsBetCollectorApiStack-{environment}'
        response = cloudformation.describe_stacks(StackName=stack_name)
        
        api_url = None
        for output in response['Stacks'][0]['Outputs']:
            if output['OutputKey'] == 'BetCollectorApiUrl':
                api_url = output['OutputValue'].rstrip('/')
                break
        
        if not api_url:
            raise Exception(f"Could not find API URL in stack {stack_name}")
        
        print(f"Testing API at: {api_url}")
        
        # Test health endpoint
        print("Testing /health endpoint...")
        health_response = requests.get(f"{api_url}/health", timeout=10)
        assert health_response.status_code == 200, f"Health check failed: {health_response.status_code}"
        
        health_data = health_response.json()
        assert health_data['status'] == 'healthy', "Health status not healthy"
        assert health_data['environment'] == environment, f"Environment mismatch: {health_data['environment']}"
        print(f"✅ Health check passed: {health_data}")
        
        # Test sports endpoint
        print("Testing /sports endpoint...")
        sports_response = requests.get(f"{api_url}/sports", timeout=10)
        assert sports_response.status_code == 200, f"Sports endpoint failed: {sports_response.status_code}"
        
        sports_data = sports_response.json()
        assert 'sports' in sports_data, "Sports data missing"
        assert isinstance(sports_data['sports'], list), "Sports should be a list"
        print(f"✅ Sports endpoint passed: Found {sports_data['count']} sports")
        
        # Test bookmakers endpoint
        print("Testing /bookmakers endpoint...")
        bookmakers_response = requests.get(f"{api_url}/bookmakers", timeout=10)
        assert bookmakers_response.status_code == 200, f"Bookmakers endpoint failed: {bookmakers_response.status_code}"
        
        bookmakers_data = bookmakers_response.json()
        assert 'bookmakers' in bookmakers_data, "Bookmakers data missing"
        assert isinstance(bookmakers_data['bookmakers'], list), "Bookmakers should be a list"
        print(f"✅ Bookmakers endpoint passed: Found {bookmakers_data['count']} bookmakers")
        
        # Test games endpoint
        print("Testing /games endpoint...")
        games_response = requests.get(f"{api_url}/games?limit=10", timeout=10)
        assert games_response.status_code == 200, f"Games endpoint failed: {games_response.status_code}"
        
        games_data = games_response.json()
        assert 'games' in games_data, "Games data missing"
        assert isinstance(games_data['games'], list), "Games should be a list"
        print(f"✅ Games endpoint passed: Found {games_data['count']} games")
        
        # Test games with sport filter (if we have sports)
        if sports_data['sports']:
            sport = sports_data['sports'][0]
            print(f"Testing /games endpoint with sport filter: {sport}")
            filtered_games_response = requests.get(f"{api_url}/games?sport={sport}&limit=5", timeout=10)
            assert filtered_games_response.status_code == 200, f"Filtered games failed: {filtered_games_response.status_code}"
            
            filtered_games_data = filtered_games_response.json()
            assert filtered_games_data['sport_filter'] == sport, "Sport filter not applied"
            print(f"✅ Filtered games endpoint passed: Found {filtered_games_data['count']} games for {sport}")
        
        # Test specific game endpoint (if we have games)
        if games_data['games']:
            game_id = games_data['games'][0]['game_id']
            print(f"Testing /games/{game_id} endpoint...")
            game_response = requests.get(f"{api_url}/games/{game_id}", timeout=10)
            assert game_response.status_code == 200, f"Game detail failed: {game_response.status_code}"
            
            game_detail = game_response.json()
            assert game_detail['game_id'] == game_id, "Game ID mismatch"
            assert 'bookmakers' in game_detail, "Bookmakers data missing"
            print(f"✅ Game detail endpoint passed: Found {game_detail['count']} bookmakers for game {game_id}")
        
        # Test non-existent game
        print("Testing /games/nonexistent endpoint...")
        nonexistent_response = requests.get(f"{api_url}/games/nonexistent", timeout=10)
        assert nonexistent_response.status_code == 404, f"Expected 404 for nonexistent game: {nonexistent_response.status_code}"
        print("✅ Non-existent game endpoint correctly returned 404")
        
        # Test CORS headers
        print("Testing CORS headers...")
        cors_response = requests.options(f"{api_url}/health", timeout=10)
        assert 'Access-Control-Allow-Origin' in cors_response.headers, "CORS headers missing"
        print("✅ CORS headers present")
        
        return True
        
    except Exception as e:
        print(f"❌ API integration test failed: {str(e)}")
        return False

if __name__ == "__main__":
    # Use default AWS credentials (IAM role or profile)
    print("Using default AWS credentials")
    
    try:
        success = test_api_integration()
        if success:
            print("\n🎉 All API integration tests passed!")
        else:
            print("\n❌ API integration tests failed!")
            exit(1)
    except Exception as e:
        print(f"\n❌ API integration test failed: {str(e)}")
        exit(1)
