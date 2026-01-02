import boto3
import json
import os
from datetime import datetime, timedelta

def test_lambda_integration():
    """Integration test to verify Lambda function updates DynamoDB with fresh data"""
    
    # Get environment-specific resources
    environment = os.getenv('ENVIRONMENT', 'dev')
    table_name = f'carpool-bets-v2-{environment}'
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(table_name)
    
    # Find the Lambda function
    functions_response = lambda_client.list_functions()
    lambda_function_name = None
    
    for func in functions_response['Functions']:
        if 'OddsCollectorFunction' in func['FunctionName']:
            lambda_function_name = func['FunctionName']
            break
    
    if not lambda_function_name:
        raise Exception("Could not find OddsCollectorFunction Lambda")
    
    print(f"Testing Lambda function: {lambda_function_name}")
    print(f"Testing DynamoDB table: {table_name}")
    
    # Record timestamp before Lambda execution
    test_start_time = datetime.utcnow() - timedelta(seconds=30)
    test_start_iso = test_start_time.isoformat()
    
    # Invoke Lambda for specific sport
    print("Invoking Lambda function for basketball_nba...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({"sport": "basketball_nba"})
    )
    
    # Verify Lambda executed successfully
    payload = json.loads(response['Payload'].read())
    print(f"Lambda response: {payload}")
    
    assert response['StatusCode'] == 200, f"Lambda invocation failed with status {response['StatusCode']}"
    assert payload['statusCode'] == 200, f"Lambda function failed: {payload.get('body', 'No error message')}"
    
    body = json.loads(payload['body'])
    print(f"Lambda execution result: {body['message']}")
    
    # Wait for DynamoDB consistency
    import time
    time.sleep(3)
    
    # Check DynamoDB using GSI for basketball_nba latest items
    updated_items_response = table.query(
        IndexName='ActiveBetsIndex',
        KeyConditionExpression='bet_type = :bet_type',
        FilterExpression='sport = :sport AND attribute_exists(latest) AND updated_at > :start_time',
        ExpressionAttributeValues={
            ':bet_type': 'GAME',
            ':sport': 'basketball_nba',
            ':start_time': test_start_iso
        },
        Limit=10
    )
    
    updated_items = updated_items_response['Items']
    assert len(updated_items) > 0, f"No items updated after {test_start_iso}"
    
    print(f"Found {len(updated_items)} items updated during this test")
    
    # Validate data structure
    for item in updated_items[:3]:
        # Verify required fields
        required_fields = ['pk', 'sk', 'bet_type', 'sport', 'updated_at']
        for field in required_fields:
            assert field in item, f"Missing required field '{field}'"
        
        # Verify data types and values
        assert item['sport'] == 'basketball_nba', f"Expected basketball_nba, got: {item['sport']}"
        assert item['bet_type'] in ['GAME', 'PROP'], f"Invalid bet_type: {item['bet_type']}"
        assert item['pk'].startswith(item['bet_type'] + '#'), f"Invalid pk format: {item['pk']}"
        
        # Verify timestamp is fresh
        updated_time = datetime.fromisoformat(item['updated_at'])
        assert updated_time >= test_start_time, f"Item timestamp not from this test run"
        
        print(f"✓ Validated item: {item['pk']} ({item['bet_type']})")
    
    print(f"✅ Integration test passed!")
    print(f"   - Lambda executed successfully")
    print(f"   - Found {len(updated_items)} fresh items")
    print(f"   - Data structure validated")
    
    return True

if __name__ == "__main__":
    try:
        test_lambda_integration()
        print("\n🎉 Integration test passed!")
    except Exception as e:
        print(f"\n❌ Integration test failed: {str(e)}")
        exit(1)
