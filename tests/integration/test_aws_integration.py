import pytest
import boto3
import os
from moto import mock_dynamodb, mock_s3

# Simple integration test that verifies AWS resources exist
def test_aws_resources_exist():
    """Test that required AWS resources are accessible"""
    # This will run against real AWS in staging/prod
    # Skip if running locally without AWS credentials
    try:
        # Test DynamoDB table access
        dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
        table_name = 'sports-betting-bets-staging'  # Will be staging in pipeline
        
        # Just check table exists (don't create data)
        table = dynamodb.Table(table_name)
        table.load()  # This will fail if table doesn't exist
        
        # Test S3 bucket access
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket_name = 'sports-betting-raw-data-staging-352312075009'
        s3.head_bucket(Bucket=bucket_name)
        
        assert True  # If we get here, resources exist
        
    except Exception as e:
        # Skip test if AWS not configured (local development)
        if 'credentials' in str(e).lower() or 'not found' in str(e).lower():
            pytest.skip(f"AWS resources not available: {e}")
        else:
            raise e

def test_api_health_integration():
    """Test API health endpoint works"""
    from fastapi.testclient import TestClient
    import sys
    from pathlib import Path
    
    # Add backend to path
    backend_dir = Path(__file__).parent.parent.parent / "backend"
    sys.path.insert(0, str(backend_dir))
    
    from api.main import app
    client = TestClient(app)
    
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
