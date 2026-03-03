import os
import sys
import unittest

os.environ["DYNAMODB_TABLE"] = "test-table"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ml.model_factory import ModelFactory  # noqa: E402


class TestModelFactory(unittest.TestCase):
    """Test ModelFactory"""

    def test_get_available_models(self):
        """Test getting list of available models"""
        models = ModelFactory.get_available_models()
        
        self.assertIsInstance(models, list)
        self.assertIn("consensus", models)
        self.assertIn("fundamentals", models)
        self.assertIn("matchup", models)
        self.assertIn("momentum", models)
        self.assertIn("value", models)
        self.assertIn("hot_cold", models)
        self.assertIn("rest_schedule", models)
        self.assertIn("injury_aware", models)
        self.assertIn("contrarian", models)
        self.assertIn("news", models)
        self.assertIn("ensemble", models)
        self.assertIn("player_stats", models)
        self.assertEqual(len(models), 12)

    def test_create_unknown_model(self):
        """Test creating unknown model raises error"""
        with self.assertRaises(ValueError) as context:
            ModelFactory.create_model("unknown_model")
        
        self.assertIn("Unknown model", str(context.exception))
        self.assertIn("unknown_model", str(context.exception))

    def test_all_models_listed(self):
        """Test all 12 models are listed"""
        models = ModelFactory.get_available_models()
        expected = [
            "player_stats", "fundamentals", "matchup", "momentum", "value",
            "hot_cold", "rest_schedule", "injury_aware", "contrarian",
            "news", "ensemble", "consensus"
        ]
        
        for model in expected:
            self.assertIn(model, models)


if __name__ == "__main__":
    unittest.main()
