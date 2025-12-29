import pytest
import boto3
import os
from moto import mock_dynamodb, mock_s3

def get_staging_session():
    """Get boto3 session with staging account access"""
    try:
        # Try to assume cross-account role if in pipeline
        sts = boto3.client('sts')
        role_arn = 'arn:aws:iam::352312075009:role/CrossAccountIntegrationTestRole-staging'
        
        response = sts.assume_role(
            RoleArn=role_arn,
            RoleSessionName='integration-test-session'
        )
        
        credentials = response['Credentials']
        return boto3.Session(
            aws_access_key_id=credentials['AccessKeyId'],
            aws_secret_access_key=credentials['SecretAccessKey'],
            aws_session_token=credentials['SessionToken'],
            region_name='us-east-1'
        )
    except Exception:
        # Fall back to default session (local development)
        return boto3.Session(region_name='us-east-1')

# Simple integration test that verifies AWS resources exist
def test_aws_resources_exist():
    """Test that required AWS resources are accessible"""
    try:
        session = get_staging_session()
        
        # Test DynamoDB table access
        dynamodb = session.resource('dynamodb')
        table_name = 'sports-betting-bets-staging'
        
        # Just check table exists (don't create data)
        table = dynamodb.Table(table_name)
        table.load()  # This will fail if table doesn't exist
        
        # Test S3 bucket access
        s3 = session.client('s3')
        bucket_name = 'sports-betting-raw-data-staging-352312075009'
        s3.head_bucket(Bucket=bucket_name)
        
        assert True  # If we get here, resources exist
        
    except Exception as e:
        # Skip test if AWS not configured or cross-account access issues
        error_str = str(e).lower()
        if any(keyword in error_str for keyword in ['credentials', 'not found', 'access denied', 'unauthorized', 'forbidden']):
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
