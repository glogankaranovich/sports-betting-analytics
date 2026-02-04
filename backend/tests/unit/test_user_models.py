"""
Unit tests for user models data layer
"""
import unittest
from decimal import Decimal
from user_models import UserModel, ModelPrediction, validate_model_config


class TestUserModel(unittest.TestCase):
    def setUp(self):
        self.valid_config = {
            "user_id": "user123",
            "name": "Test Model",
            "description": "A test model for unit testing",
            "sport": "basketball_nba",
            "bet_types": ["h2h", "spreads"],
            "data_sources": {
                "team_stats": {"enabled": True, "weight": 0.5},
                "odds_movement": {"enabled": True, "weight": 0.5},
            },
            "min_confidence": 0.6,
        }

    def test_create_user_model(self):
        """Test creating a user model"""
        model = UserModel(**self.valid_config)

        self.assertEqual(model.user_id, "user123")
        self.assertEqual(model.name, "Test Model")
        self.assertEqual(model.sport, "basketball_nba")
        self.assertEqual(len(model.bet_types), 2)
        self.assertEqual(model.min_confidence, 0.6)
        self.assertIsNotNone(model.model_id)
        self.assertEqual(model.status, "active")

    def test_to_dynamodb(self):
        """Test converting model to DynamoDB format"""
        model = UserModel(**self.valid_config)
        item = model.to_dynamodb()

        self.assertEqual(item["PK"], f"USER#{model.user_id}")
        self.assertEqual(item["SK"], f"MODEL#{model.model_id}")
        self.assertEqual(item["name"], "Test Model")
        self.assertIsInstance(item["min_confidence"], Decimal)

    def test_from_dynamodb(self):
        """Test creating model from DynamoDB item"""
        model = UserModel(**self.valid_config)
        item = model.to_dynamodb()

        restored = UserModel.from_dynamodb(item)

        self.assertEqual(restored.user_id, model.user_id)
        self.assertEqual(restored.name, model.name)
        self.assertEqual(restored.model_id, model.model_id)
        self.assertEqual(restored.min_confidence, model.min_confidence)


class TestModelPrediction(unittest.TestCase):
    def setUp(self):
        self.prediction_data = {
            "model_id": "model123",
            "user_id": "user123",
            "game_id": "game456",
            "sport": "basketball_nba",
            "prediction": "Lakers",
            "confidence": 0.75,
            "reasoning": "Strong team stats",
            "bet_type": "h2h",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "commence_time": "2026-02-04T19:00:00Z",
        }

    def test_create_prediction(self):
        """Test creating a prediction"""
        pred = ModelPrediction(**self.prediction_data)

        self.assertEqual(pred.model_id, "model123")
        self.assertEqual(pred.prediction, "Lakers")
        self.assertEqual(pred.confidence, 0.75)
        self.assertEqual(pred.outcome, "pending")

    def test_to_dynamodb(self):
        """Test converting prediction to DynamoDB format"""
        pred = ModelPrediction(**self.prediction_data)
        item = pred.to_dynamodb()

        self.assertEqual(item["PK"], f"MODEL#{pred.model_id}")
        self.assertTrue(item["SK"].startswith(f"GAME#{pred.game_id}"))
        self.assertIsInstance(item["confidence"], Decimal)


class TestValidateModelConfig(unittest.TestCase):
    def test_valid_config(self):
        """Test validation of valid config"""
        config = {
            "name": "Valid Model",
            "description": "This is a valid model configuration",
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {"team_stats": {"enabled": True, "weight": 1.0}},
            "min_confidence": 0.6,
        }

        valid, error = validate_model_config(config)
        self.assertTrue(valid)
        self.assertIsNone(error)

    def test_missing_required_field(self):
        """Test validation fails for missing field"""
        config = {
            "name": "Invalid Model",
            # Missing description
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {},
            "min_confidence": 0.6,
        }

        valid, error = validate_model_config(config)
        self.assertFalse(valid)
        self.assertIn("description", error)

    def test_invalid_name_length(self):
        """Test validation fails for invalid name length"""
        config = {
            "name": "AB",  # Too short
            "description": "Valid description",
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {"team_stats": {"enabled": True, "weight": 1.0}},
            "min_confidence": 0.6,
        }

        valid, error = validate_model_config(config)
        self.assertFalse(valid)
        self.assertIn("3-50 characters", error)

    def test_invalid_weights_sum(self):
        """Test validation fails when weights don't sum to 100%"""
        config = {
            "name": "Invalid Weights",
            "description": "Model with invalid weights",
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {
                "team_stats": {"enabled": True, "weight": 0.3},
                "odds_movement": {"enabled": True, "weight": 0.3},
            },
            "min_confidence": 0.6,
        }

        valid, error = validate_model_config(config)
        self.assertFalse(valid)
        self.assertIn("100%", error)

    def test_no_enabled_sources(self):
        """Test validation fails when no sources enabled"""
        config = {
            "name": "No Sources",
            "description": "Model with no enabled sources",
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {"team_stats": {"enabled": False, "weight": 1.0}},
            "min_confidence": 0.6,
        }

        valid, error = validate_model_config(config)
        self.assertFalse(valid)
        self.assertIn("enabled", error)

    def test_invalid_confidence_range(self):
        """Test validation fails for invalid confidence range"""
        config = {
            "name": "Invalid Confidence",
            "description": "Model with invalid confidence",
            "sport": "basketball_nba",
            "bet_types": ["h2h"],
            "data_sources": {"team_stats": {"enabled": True, "weight": 1.0}},
            "min_confidence": 0.3,  # Too low
        }

        valid, error = validate_model_config(config)
        self.assertFalse(valid)
        self.assertIn("50%", error)


if __name__ == "__main__":
    unittest.main()
