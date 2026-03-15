"""Unit tests for FeatureExtractor"""
import unittest
from benny.feature_extractor import FeatureExtractor


class TestFeatureExtractor(unittest.TestCase):
    
    def test_extract_features_home_bet(self):
        """Test feature extraction for home team bet"""
        game_data = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "sport": "basketball_nba"
        }
        
        features = FeatureExtractor.extract_features(
            game_data=game_data,
            home_elo=1600,
            away_elo=1500,
            fatigue={"home_fatigue_score": 20, "away_fatigue_score": 50},
            home_injuries=[{"impact": "high"}],
            away_injuries=[{"impact": "high"}, {"impact": "medium"}],
            home_form={"streak": "W3"},
            away_form={"streak": "L2"},
            weather={"impact_level": "moderate"},
            h2h_history=[{"winner": "Lakers"}, {"winner": "Warriors"}],
            odds=-110,
            market_key="h2h",
            prediction="Lakers"
        )
        
        self.assertEqual(features["elo_diff"], 100)
        self.assertEqual(features["fatigue_score"], 20)
        self.assertEqual(features["fatigue_advantage"], 30)
        self.assertEqual(features["injury_count"], 1)
        self.assertEqual(features["form_streak"], 3)
        self.assertEqual(features["weather_impact"], 2)
        self.assertTrue(features["is_home"])
        self.assertTrue(features["is_favorite"])
        self.assertEqual(features["sport"], "basketball_nba")
    
    def test_extract_features_away_bet(self):
        """Test feature extraction for away team bet"""
        game_data = {
            "home_team": "Lakers",
            "away_team": "Warriors",
            "sport": "basketball_nba"
        }
        
        features = FeatureExtractor.extract_features(
            game_data=game_data,
            home_elo=1600,
            away_elo=1500,
            fatigue={"home_fatigue_score": 20, "away_fatigue_score": 50},
            home_injuries=[],
            away_injuries=[],
            home_form={"streak": "W2"},
            away_form={"streak": "L1"},
            weather=None,
            h2h_history=[],
            odds=150,
            market_key="h2h",
            prediction="Warriors"
        )
        
        self.assertEqual(features["elo_diff"], 100)
        self.assertEqual(features["fatigue_score"], 50)
        self.assertEqual(features["fatigue_advantage"], -30)
        self.assertFalse(features["is_home"])
        self.assertFalse(features["is_favorite"])
    
    def test_parse_streak(self):
        """Test streak parsing"""
        self.assertEqual(FeatureExtractor._parse_streak("W3"), 3)
        self.assertEqual(FeatureExtractor._parse_streak("L2"), -2)
        self.assertEqual(FeatureExtractor._parse_streak(""), 0)
        self.assertEqual(FeatureExtractor._parse_streak("W"), 1)
        self.assertEqual(FeatureExtractor._parse_streak("L"), -1)
    
    def test_odds_to_probability(self):
        """Test odds conversion"""
        # Negative odds (favorite)
        prob = FeatureExtractor._odds_to_probability(-110)
        self.assertAlmostEqual(prob, 0.5238, places=3)
        
        # Positive odds (underdog)
        prob = FeatureExtractor._odds_to_probability(150)
        self.assertAlmostEqual(prob, 0.4, places=3)
        
        # Even odds
        prob = FeatureExtractor._odds_to_probability(100)
        self.assertEqual(prob, 0.5)


if __name__ == '__main__':
    unittest.main()
