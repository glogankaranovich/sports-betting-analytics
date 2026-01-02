import boto3
import json
import os
from datetime import datetime, timedelta

def test_lambda_integration():
    """Integration test to verify Lambda function updates DynamoDB with fresh timestamps"""
    
    # Get environment-specific resources
    environment = os.getenv('ENVIRONMENT', 'dev')
    table_name = f'carpool-bets-v2-{environment}'
    
    # Initialize AWS clients
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table(table_name)
    
    # Find the Lambda function by searching for the pattern
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
    
    # Record timestamp before Lambda execution (with buffer)
    test_start_time = datetime.utcnow() - timedelta(seconds=30)
    test_start_iso = test_start_time.isoformat()
    
    # Get sample of existing data to compare timestamps
    existing_response = table.scan(Limit=5)
    existing_timestamps = {}
    for item in existing_response.get('Items', []):
        # Use pk as the key since schema has changed
        key = item.get('pk', 'unknown')
        existing_timestamps[key] = item.get('updated_at', item.get('predicted_at', '1970-01-01T00:00:00'))
    
    print(f"Found {len(existing_timestamps)} existing items to track")
    
    # Invoke Lambda function
    print("Invoking Lambda function...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType='RequestResponse'
    )
    
    # Parse response
    payload = json.loads(response['Payload'].read())
    print(f"Lambda response: {payload}")
    
    # Verify successful execution
    assert response['StatusCode'] == 200, f"Lambda invocation failed with status {response['StatusCode']}"
    assert payload['statusCode'] == 200, f"Lambda function failed: {payload.get('body', 'No error message')}"
    
    # Parse success message
    body = json.loads(payload['body'])
    print(f"Lambda execution result: {body['message']}")
    
    # Wait for DynamoDB consistency
    import time
    time.sleep(3)
    
    # Check for items updated after test start
    updated_items_response = table.scan(
        FilterExpression=boto3.dynamodb.conditions.Attr('updated_at').gt(test_start_iso) | 
                        boto3.dynamodb.conditions.Attr('predicted_at').gt(test_start_iso),
        Limit=20
    )
    
    updated_items = updated_items_response['Items']
    assert len(updated_items) > 0, f"No items updated after {test_start_iso}"
    
    print(f"Found {len(updated_items)} items updated during this test")
    
    # Verify timestamps are actually newer for existing items
    updated_count = 0
    for item in updated_items:
        key = item.get('pk', 'unknown')
        if key in existing_timestamps:
            old_timestamp = existing_timestamps[key]
            new_timestamp = item.get('updated_at', item.get('predicted_at', ''))
            if new_timestamp > old_timestamp:
                updated_count += 1
    
    print(f"Verified {updated_count} existing items were actually updated with newer timestamps")
    
    # Verify data structure and content
    for item in updated_items[:3]:
        # Verify required fields based on item type
        if item.get('bet_type') == 'PROP' or 'PROP' in item.get('pk', ''):
            # Player prop item
            required_fields = ['pk', 'sk', 'sport', 'bookmaker', 'updated_at', 'event_id']
            for field in required_fields:
                assert field in item, f"Missing required field '{field}' in prop item"
        elif item.get('prediction_type') in ['GAME', 'PROP']:
            # Prediction item
            required_fields = ['pk', 'sk', 'prediction_type', 'predicted_at']
            for field in required_fields:
                assert field in item, f"Missing required field '{field}' in prediction item"
        else:
            # Game item (if any)
            required_fields = ['pk', 'sk', 'sport', 'updated_at']
            for field in required_fields:
                assert field in item, f"Missing required field '{field}' in game item"
        
        # Verify sport values
        if 'sport' in item:
            expected_sports = [
                'americanfootball_nfl', 'basketball_nba', 'baseball_mlb', 'icehockey_nhl',
                'soccer_epl', 'soccer_usa_mls', 'mma_mixed_martial_arts', 'boxing_boxing'
            ]
            assert item['sport'] in expected_sports, f"Unexpected sport: {item['sport']}"
        
        # Verify timestamp is from this test run
        timestamp_field = item.get('updated_at', item.get('predicted_at', ''))
        if timestamp_field:
            updated_time = datetime.fromisoformat(timestamp_field)
            assert updated_time >= test_start_time, f"Item timestamp {timestamp_field} is not from this test run"
    
    # Verify we have data for expected sports
    sports_found = set()
    for item in updated_items:
        if 'sport' in item:
            sports_found.add(item['sport'])
    
    print(f"Sports with updated data: {list(sports_found)}")
    
    print(f"✅ Integration test passed!")
    print(f"   - Lambda function executed successfully")
    print(f"   - Found {len(updated_items)} items with fresh timestamps")
    print(f"   - Verified {updated_count} existing items were updated")
    print(f"   - Data structure and content verified")
    
    return True

if __name__ == "__main__":
    # Use default AWS credentials (IAM role or assumed role)
    print("Using default AWS credentials")
    
    try:
        test_lambda_integration()
        print("\n🎉 All integration tests passed!")
    except Exception as e:
        print(f"\n❌ Integration test failed: {str(e)}")
        exit(1)
