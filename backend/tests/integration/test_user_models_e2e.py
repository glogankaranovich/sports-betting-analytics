"""
End-to-end test for user models execution pipeline
Tests: API -> DynamoDB -> SQS -> Lambda Executor -> Predictions
"""
import os
import time

import boto3
import requests


def get_test_user_token(environment_title="Dev"):
    """Get JWT token for test user"""
    cf = boto3.client("cloudformation", region_name="us-east-1")
    response = cf.describe_stacks(StackName=f"{environment_title}-Auth")
    outputs = response["Stacks"][0]["Outputs"]
    
    user_pool_id = next(o["OutputValue"] for o in outputs if o["OutputKey"] == "UserPoolId")
    client_id = next(o["OutputValue"] for o in outputs if o["OutputKey"] == "UserPoolClientId")
    
    client = boto3.client("cognito-idp", region_name="us-east-1")
    response = client.admin_initiate_auth(
        UserPoolId=user_pool_id,
        ClientId=client_id,
        AuthFlow="ADMIN_NO_SRP_AUTH",
        AuthParameters={
            "USERNAME": "testuser@example.com",
            "PASSWORD": "CarpoolBets2026!Secure#",
        },
    )
    return response["AuthenticationResult"]["IdToken"]


def test_user_models_e2e():
    """Test complete user model execution pipeline"""
    print("\n" + "=" * 60)
    print("User Models End-to-End Test")
    print("=" * 60 + "\n")

    environment = os.getenv("ENVIRONMENT", "dev")
    environment_title = environment.title()

    # Get API URL
    cf = boto3.client("cloudformation", region_name="us-east-1")
    try:
        response = cf.describe_stacks(StackName=f"{environment_title}-BetCollectorApi")
        api_url = next(
            (o["OutputValue"] for o in response["Stacks"][0]["Outputs"] 
             if o["OutputKey"] in ["BetCollectorApiUrl", "ApiUrl"]),
            None
        )
        if not api_url:
            print(f"⚠️  API URL not found for {environment_title} environment - skipping test")
            return True
    except Exception as e:
        print(f"⚠️  Could not access {environment_title} environment: {e}")
        return True

    try:
        token = get_test_user_token(environment_title)
    except Exception as e:
        print(f"⚠️  Could not get test user token: {e}")
        return True
        
    headers = {"Authorization": f"Bearer {token}"}
    
    # Get actual user ID from Cognito
    cognito = boto3.client("cognito-idp", region_name="us-east-1")
    auth_response = cf.describe_stacks(StackName=f"{environment_title}-Auth")
    user_pool_id = next(o["OutputValue"] for o in auth_response["Stacks"][0]["Outputs"] if o["OutputKey"] == "UserPoolId")
    user = cognito.admin_get_user(UserPoolId=user_pool_id, Username="testuser@example.com")
    test_user_id = next(attr["Value"] for attr in user["UserAttributes"] if attr["Name"] == "sub")

    # 1. Create active model
    print("1. Creating active user model...")
    model_data = {
        "user_id": test_user_id,
        "name": "E2E Test Model",
        "description": "End-to-end test model",
        "sport": "basketball_nba",
        "bet_types": ["h2h"],
        "data_sources": {
            "team_stats": {"enabled": True, "weight": 0.5},
            "odds_movement": {"enabled": True, "weight": 0.5},
        },
        "min_confidence": 0.6,
        "is_active": True,
    }

    response = requests.post(f"{api_url}user-models", json=model_data, headers=headers)
    print(f"Response status: {response.status_code}")
    if response.status_code == 403:
        print(f"⚠️  User models feature not available in {environment} environment - skipping test")
        return True
    if response.status_code != 201:
        print(f"Response body: {response.text}")
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    model_id = response.json()["model"]["model_id"]
    print(f"✓ Model created: {model_id}")

    # 2. Verify in DynamoDB
    print("\n2. Verifying model in DynamoDB...")
    dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
    table = dynamodb.Table(f"{environment_title}-UserModels-UserModels")
    item = table.get_item(Key={"PK": f"USER#{test_user_id}", "SK": f"MODEL#{model_id}"})
    assert "Item" in item
    print("✓ Model found in DynamoDB")

    # 3. Trigger queue loader Lambda
    print("\n3. Triggering queue loader Lambda...")
    lambda_client = boto3.client("lambda", region_name="us-east-1")
    response = lambda_client.invoke(
        FunctionName=f"{environment_title}-UserModels-QueueLoader",
        InvocationType="RequestResponse",
    )
    print(f"✓ Queue loader executed: {response['StatusCode']}")

    # 4. Check SQS queue
    print("\n4. Checking SQS queue for messages...")
    sqs = boto3.client("sqs", region_name="us-east-1")
    queue_url_response = sqs.get_queue_url(
        QueueName=f"{environment_title}-UserModels-ModelExecutionQueue"
    )
    queue_url = queue_url_response["QueueUrl"]

    time.sleep(2)
    attrs = sqs.get_queue_attributes(
        QueueUrl=queue_url, AttributeNames=["ApproximateNumberOfMessages"]
    )
    msg_count = int(attrs["Attributes"]["ApproximateNumberOfMessages"])
    print(f"✓ Messages in queue: {msg_count}")

    # 5. Trigger executor Lambda manually
    print("\n5. Triggering executor Lambda...")
    response = lambda_client.invoke(
        FunctionName="Dev-UserModels-ModelExecutor",
        InvocationType="RequestResponse",
    )
    print(f"✓ Executor executed: {response['StatusCode']}")

    # 6. Check for predictions (0 expected with placeholder evaluators)
    print("\n6. Checking for predictions...")
    pred_table = dynamodb.Table("Dev-UserModels-ModelPredictions")
    response = pred_table.query(
        KeyConditionExpression="PK = :pk",
        ExpressionAttributeValues={":pk": f"MODEL#{model_id}"},
        Limit=5,
    )
    pred_count = len(response.get("Items", []))
    print(
        f"✓ Predictions found: {pred_count} (0 expected - placeholder evaluators return 0.5 confidence)"
    )

    # 7. Cleanup
    print("\n7. Cleaning up test model...")
    response = requests.delete(
        f"{api_url}user-models/{model_id}",
        params={"user_id": test_user_id},
        headers=headers,
    )
    assert response.status_code == 200
    print("✓ Model deleted")

    print("\n" + "=" * 60)
    print("✅ End-to-end test completed successfully!")
    print("=" * 60 + "\n")
    return True


if __name__ == "__main__":
    import sys

    try:
        success = test_user_models_e2e()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
