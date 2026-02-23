"""
Real integration tests for user models system against deployed AWS resources
"""
import os
import unittest
from decimal import Decimal

import boto3


class TestUserModelsRealIntegration(unittest.TestCase):
    """Test user models against real DynamoDB tables"""

    @classmethod
    def setUpClass(cls):
        """Setup connections to real AWS resources"""
        environment = os.getenv("ENVIRONMENT", "dev")
        environment_title = environment.title()
        
        cls.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        
        try:
            cls.user_models_table = cls.dynamodb.Table(f"{environment_title}-UserModels-UserModels")
            cls.predictions_table = cls.dynamodb.Table(f"{environment_title}-UserModels-ModelPredictions")
            cls.test_user_id = "test_integration_user"
            cls.environment = environment
        except Exception as e:
            print(f"⚠️  Could not access user models tables in {environment_title}: {e}")
            cls.user_models_table = None
            cls.predictions_table = None

    def setUp(self):
        """Check if tables are available"""
        if not self.user_models_table:
            self.skipTest(f"User models tables not available in {self.environment}")

    def tearDown(self):
        """Clean up test data after each test"""
        if not self.user_models_table:
            return
            
        # Delete test user's models
        try:
            response = self.user_models_table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": f"USER#{self.test_user_id}"},
            )
            for item in response.get("Items", []):
                self.user_models_table.delete_item(
                    Key={"PK": item["PK"], "SK": item["SK"]}
                )
        except Exception as e:
            print(f"Cleanup error: {e}")

    def test_create_and_retrieve_model(self):
        """Test creating and retrieving a user model"""
        import uuid
        from datetime import datetime

        # Create model directly in DynamoDB
        model_id = f"model_{uuid.uuid4().hex[:12]}"
        created_at = datetime.utcnow().isoformat()

        item = {
            "PK": f"USER#{self.test_user_id}",
            "SK": f"MODEL#{model_id}",
            "GSI1PK": f"USER#{self.test_user_id}",
            "GSI1SK": f"CREATED#{created_at}",
            "model_id": model_id,
            "user_id": self.test_user_id,
            "name": "Integration Test Model",
            "description": "Testing end-to-end model creation",
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {"team_stats": {"enabled": True, "weight": Decimal("1.0")}},
            "min_confidence": Decimal("0.6"),
            "status": "active",
            "created_at": created_at,
            "updated_at": created_at,
        }

        self.user_models_table.put_item(Item=item)

        # Retrieve it
        response = self.user_models_table.get_item(
            Key={"PK": f"USER#{self.test_user_id}", "SK": f"MODEL#{model_id}"}
        )

        retrieved = response.get("Item")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["name"], "Integration Test Model")
        self.assertEqual(retrieved["sport"], "basketball_nba")
        print("✅ Model created and retrieved successfully")

    def test_list_user_models(self):
        """Test listing all models for a user"""
        import uuid
        from datetime import datetime

        # Create multiple models
        model_ids = []
        for i in range(3):
            model_id = f"model_{uuid.uuid4().hex[:12]}"
            model_ids.append(model_id)
            created_at = datetime.utcnow().isoformat()

            item = {
                "PK": f"USER#{self.test_user_id}",
                "SK": f"MODEL#{model_id}",
                "GSI1PK": f"USER#{self.test_user_id}",
                "GSI1SK": f"CREATED#{created_at}",
                "model_id": model_id,
                "user_id": self.test_user_id,
                "name": f"Test Model {i}",
                "description": "Test",
                "sport": "basketball_nba",
                "bet_types": ["h2h"],
                "data_sources": {
                    "team_stats": {"enabled": True, "weight": Decimal("1.0")}
                },
                "min_confidence": Decimal("0.6"),
                "status": "active",
                "created_at": created_at,
                "updated_at": created_at,
            }

            self.user_models_table.put_item(Item=item)

        # List models
        response = self.user_models_table.query(
            KeyConditionExpression="PK = :pk",
            ExpressionAttributeValues={":pk": f"USER#{self.test_user_id}"},
        )

        models = response.get("Items", [])
        self.assertGreaterEqual(len(models), 3)
        print(f"✅ Listed {len(models)} models for user")


if __name__ == "__main__":
    unittest.main()
