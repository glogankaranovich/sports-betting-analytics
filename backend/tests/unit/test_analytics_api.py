"""
Unit tests for analytics API handler
"""
import os
import unittest
from unittest.mock import patch, MagicMock, Mock
import json

os.environ["DYNAMODB_TABLE"] = "test-table"

from api.analytics import AnalyticsHandler


class TestAnalyticsHandler(unittest.TestCase):
    """Test analytics API handler"""

    def setUp(self):
        self.handler = AnalyticsHandler()

    @patch("api.analytics.table")
    def test_route_get_analytics(self, mock_table):
        """Test routing to get analytics"""
        with patch.object(self.handler, "get_analytics") as mock_get:
            mock_get.return_value = {"statusCode": 200}
            
            result = self.handler.route_request("GET", "/analytics", {}, {}, {})
            mock_get.assert_called_once()

    @patch("api.analytics.table")
    def test_route_model_performance(self, mock_table):
        """Test routing to model performance"""
        with patch.object(self.handler, "get_model_performance") as mock_get:
            mock_get.return_value = {"statusCode": 200}
            
            result = self.handler.route_request("GET", "/model-performance", {"model": "consensus"}, {}, {})
            mock_get.assert_called_once()

    @patch("api.analytics.table")
    def test_route_model_comparison(self, mock_table):
        """Test routing to model comparison"""
        with patch.object(self.handler, "get_model_comparison") as mock_get:
            mock_get.return_value = {"statusCode": 200}
            
            result = self.handler.route_request("GET", "/model-comparison", {}, {}, {})
            mock_get.assert_called_once()

    @patch("api.analytics.table")
    def test_route_model_rankings(self, mock_table):
        """Test routing to model rankings"""
        with patch.object(self.handler, "get_model_rankings") as mock_get:
            mock_get.return_value = {"statusCode": 200}
            
            result = self.handler.route_request("GET", "/model-rankings", {}, {}, {})
            mock_get.assert_called_once()

    @patch("api.analytics.table")
    def test_route_not_found(self, mock_table):
        """Test routing to invalid endpoint"""
        result = self.handler.route_request("GET", "/invalid", {}, {}, {})
        self.assertEqual(result["statusCode"], 404)

    @patch("api.analytics.table")
    def test_get_analytics_summary(self, mock_table):
        """Test getting analytics summary"""
        mock_table.query.return_value = {
            "Items": [{
                "pk": "ANALYTICS#summary",
                "data": {
                    "total_predictions": 1000,
                    "overall_accuracy": 0.65
                }
            }]
        }

        result = self.handler.get_analytics({"type": "summary"})
        
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("total_predictions", body)

    @patch("ml.dynamic_weighting.DynamicModelWeighting")
    @patch("api.analytics.table")
    def test_get_analytics_weights(self, mock_table, mock_weighting_class):
        """Test getting model weights"""
        mock_weighting_instance = MagicMock()
        # Return weights for all 10 models the code expects
        mock_weighting_instance.get_model_weights.return_value = {
            "consensus": 0.35, "value": 0.25, "momentum": 0.20, "contrarian": 0.20,
            "hot_cold": 0.0, "rest_schedule": 0.0, "matchup": 0.0, 
            "injury_aware": 0.0, "ensemble": 0.0, "benny": 0.0
        }
        mock_weighting_instance.get_recent_accuracy.return_value = 0.65
        mock_weighting_instance.get_recent_brier_score.return_value = 0.20
        mock_weighting_instance.lookback_days = 30
        mock_weighting_class.return_value = mock_weighting_instance
        
        result = self.handler.get_analytics({
            "type": "weights",
            "sport": "basketball_nba",
            "bet_type": "game"
        })
        
        self.assertEqual(result["statusCode"], 200)
        body = json.loads(result["body"])
        self.assertIn("model_weights", body)

    @patch("api.analytics.table")
    def test_get_model_performance(self, mock_table):
        """Test getting model performance"""
        mock_table.scan.return_value = {
            "Items": [{
                "model": "consensus",
                "accuracy": 0.65,
                "total_predictions": 100
            }]
        }

        result = self.handler.get_model_performance({"days": "30"})
        
        self.assertEqual(result["statusCode"], 200)

    @patch("api.analytics.table")
    def test_get_model_comparison(self, mock_table):
        """Test model comparison"""
        mock_table.scan.return_value = {
            "Items": [{
                "model": "consensus",
                "sport": "basketball_nba",
                "accuracy": 0.65
            }]
        }

        result = self.handler.get_model_comparison({
            "models": "consensus,value",
            "sport": "basketball_nba"
        })
        
        self.assertEqual(result["statusCode"], 200)

    @patch("api.analytics.table")
    def test_get_model_rankings(self, mock_table):
        """Test model rankings"""
        mock_table.scan.return_value = {
            "Items": [{
                "model": "consensus",
                "roi": 5.2,
                "accuracy": 0.65
            }]
        }

        result = self.handler.get_model_rankings({"sport": "basketball_nba"})
        
        self.assertEqual(result["statusCode"], 200)

    def test_invalid_endpoint(self):
        """Test invalid endpoint returns 404"""
        result = self.handler.route_request("GET", "/invalid", {}, {}, {})
        self.assertEqual(result["statusCode"], 404)


if __name__ == "__main__":
    unittest.main()
