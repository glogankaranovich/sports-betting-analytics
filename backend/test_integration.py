import boto3
import json
import os
from datetime import datetime, timedelta

def test_odds_collector_integration():
    """Test odds collector Lambda function"""
    
    environment = os.getenv('ENVIRONMENT', 'dev')
    table_name = f'carpool-bets-v2-{environment}'
    
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
    
    print(f"Testing odds collector: {lambda_function_name}")
    
    # Test with limit for faster execution
    test_start_time = datetime.utcnow() - timedelta(seconds=30)
    test_start_iso = test_start_time.isoformat()
    
    print("Testing odds collection with limit=2...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({"sport": "basketball_nba", "limit": 2})
    )
    
    payload = json.loads(response['Payload'].read())
    assert response['StatusCode'] == 200, f"Lambda failed: {response['StatusCode']}"
    assert payload['statusCode'] == 200, f"Function failed: {payload.get('body')}"
    
    body = json.loads(payload['body'])
    print(f"✓ Odds collection result: {body['message']}")
    
    # Verify data in DynamoDB
    import time
    print("⏳ Waiting 10 seconds for GSI eventual consistency...")
    time.sleep(10)
    
    print(f"🔍 Querying for records updated after: {test_start_iso}")
    updated_items_response = table.query(
        IndexName='ActiveBetsIndex',
        KeyConditionExpression='bet_type = :bet_type',
        FilterExpression='sport = :sport AND updated_at > :start_time',
        ExpressionAttributeValues={
            ':bet_type': 'GAME',
            ':sport': 'basketball_nba',
            ':start_time': test_start_iso
        },
        Limit=5
    )
    
    updated_items = updated_items_response['Items']
    print(f"📊 Query returned {len(updated_items)} items")
    if len(updated_items) > 0:
        print(f"📅 First item timestamp: {updated_items[0].get('updated_at')}")
    
    assert len(updated_items) > 0, "No odds data found"
    print(f"✓ Found {len(updated_items)} odds records")
    
    return True

def test_props_collector_integration():
    """Test props collector Lambda function"""
    
    environment = os.getenv('ENVIRONMENT', 'dev')
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Find the Lambda function
    functions_response = lambda_client.list_functions()
    lambda_function_name = None
    
    for func in functions_response['Functions']:
        if 'OddsCollectorFunction' in func['FunctionName']:
            lambda_function_name = func['FunctionName']
            break
    
    if not lambda_function_name:
        raise Exception("Could not find OddsCollectorFunction Lambda")
    
    print(f"Testing props collector: {lambda_function_name}")
    
    print("Testing props collection with limit=1...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({"sport": "basketball_nba", "props_only": True, "limit": 1})
    )
    
    payload = json.loads(response['Payload'].read())
    assert response['StatusCode'] == 200, f"Lambda failed: {response['StatusCode']}"
    assert payload['statusCode'] == 200, f"Function failed: {payload.get('body')}"
    
    body = json.loads(payload['body'])
    print(f"✓ Props collection result: {body['message']}")
    
    return True

def test_prediction_generator_integration():
    """Test prediction generator Lambda function"""
    
    environment = os.getenv('ENVIRONMENT', 'dev')
    lambda_client = boto3.client('lambda', region_name='us-east-1')
    
    # Find the Lambda function
    functions_response = lambda_client.list_functions()
    lambda_function_name = None
    
    for func in functions_response['Functions']:
        if 'PredictionGenerator' in func['FunctionName']:
            lambda_function_name = func['FunctionName']
            break
    
    if not lambda_function_name:
        print("⚠️  PredictionGenerator function not found - skipping test")
        return True
    
    print(f"Testing prediction generator: {lambda_function_name}")
    
    # Test game predictions
    print("Testing game predictions with limit=2...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({
            "sport": "basketball_nba", 
            "bet_type": "games", 
            "model": "consensus",
            "limit": 2
        })
    )
    
    payload = json.loads(response['Payload'].read())
    assert response['StatusCode'] == 200, f"Lambda failed: {response['StatusCode']}"
    assert payload['statusCode'] == 200, f"Function failed: {payload.get('body')}"
    
    body = json.loads(payload['body'])
    print(f"✓ Game predictions result: {body['message']}")
    
    # Test prop predictions
    print("Testing prop predictions with limit=2...")
    response = lambda_client.invoke(
        FunctionName=lambda_function_name,
        InvocationType='RequestResponse',
        Payload=json.dumps({
            "sport": "basketball_nba", 
            "bet_type": "props", 
            "model": "consensus",
            "limit": 2
        })
    )
    
    payload = json.loads(response['Payload'].read())
    assert response['StatusCode'] == 200, f"Lambda failed: {response['StatusCode']}"
    assert payload['statusCode'] == 200, f"Function failed: {payload.get('body')}"
    
    body = json.loads(payload['body'])
    print(f"✓ Prop predictions result: {body['message']}")
    
    return True

def test_lambda_integration():
    """Run all integration tests"""
    
    print("🧪 Running collector integration tests...\n")
    
    try:
        print("1. Testing Odds Collector...")
        test_odds_collector_integration()
        print()
        
        print("2. Testing Props Collector...")
        test_props_collector_integration()
        print()
        
        print("3. Testing Prediction Generator...")
        test_prediction_generator_integration()
        print()
        
        print("✅ All collector integration tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        test_lambda_integration()
        print("\n🎉 All integration tests passed!")
    except Exception as e:
        print(f"\n❌ Integration tests failed: {str(e)}")
        exit(1)
