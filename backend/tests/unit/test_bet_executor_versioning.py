"""Unit tests for BetExecutor with versioning"""
import unittest
from unittest.mock import Mock, MagicMock
from decimal import Decimal
from benny.bet_executor import BetExecutor


class TestBetExecutorVersioning(unittest.TestCase):
    
    def setUp(self):
        self.mock_table = Mock()
        self.mock_sqs = Mock()
        self.queue_url = "https://sqs.us-east-1.amazonaws.com/123/test-queue"
    
    def test_place_bet_v1_no_features(self):
        """Test v1 bet placement without features"""
        executor = BetExecutor(self.mock_table, self.mock_sqs, self.queue_url, version="v1")
        
        opportunity = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "prediction": "Lakers",
            "confidence": 0.75,
            "reasoning": "Test reasoning",
            "key_factors": ["factor1"],
            "commence_time": "2024-01-01T00:00:00Z",
            "market_key": "h2h",
            "odds": -110
        }
        
        result = executor.place_bet(opportunity, Decimal("10.00"), Decimal("100.00"))
        
        # Check that bet was stored with correct pk
        call_args = self.mock_table.put_item.call_args_list[0]
        bet_item = call_args[1]["Item"]
        
        self.assertEqual(bet_item["pk"], "BENNY")
        self.assertEqual(bet_item["version"], "v1")
        self.assertNotIn("features", bet_item)
    
    def test_place_bet_v2_with_features(self):
        """Test v2 bet placement with features"""
        executor = BetExecutor(self.mock_table, self.mock_sqs, self.queue_url, version="v3")
        
        opportunity = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "prediction": "Lakers",
            "confidence": 0.75,
            "reasoning": "Test reasoning",
            "key_factors": ["factor1"],
            "commence_time": "2024-01-01T00:00:00Z",
            "market_key": "h2h",
            "odds": -110
        }
        
        features = {
            "elo_diff": 100,
            "fatigue_score": 20,
            "is_home": True
        }
        
        result = executor.place_bet(opportunity, Decimal("10.00"), Decimal("100.00"), features)
        
        # Check that bet was stored with correct pk and features
        call_args = self.mock_table.put_item.call_args_list[0]
        bet_item = call_args[1]["Item"]
        
        self.assertEqual(bet_item["pk"], "BENNY_V3")
        self.assertEqual(bet_item["version"], "v3")
        # V3 doesn't use features, so they're not stored even if passed
    
    def test_notification_includes_version(self):
        """Test that notifications include version"""
        executor = BetExecutor(self.mock_table, self.mock_sqs, self.queue_url, version="v1")
        
        opportunity = {
            "game_id": "test123",
            "sport": "basketball_nba",
            "home_team": "Lakers",
            "away_team": "Warriors",
            "prediction": "Lakers",
            "confidence": 0.75,
            "reasoning": "Test reasoning",
            "key_factors": ["factor1"],
            "commence_time": "2024-01-01T00:00:00Z",
            "market_key": "h2h",
            "odds": -110,
            "expected_value": 0.1
        }
        
        import os
        os.environ['ENVIRONMENT'] = 'dev'
        
        result = executor.place_bet(opportunity, Decimal("10.00"), Decimal("100.00"))
        
        # Check SQS message includes version
        self.mock_sqs.send_message.assert_called_once()
        call_args = self.mock_sqs.send_message.call_args
        
        import json
        message_body = json.loads(call_args[1]["MessageBody"])
        self.assertEqual(message_body["data"]["version"], "v1")


if __name__ == '__main__':
    unittest.main()
