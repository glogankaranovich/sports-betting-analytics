import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime

class PredictionEngine:
    def __init__(self):
        self.win_model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.spread_model = LogisticRegression(random_state=42)
        self.total_model = LogisticRegression(random_state=42)
        self.scaler = StandardScaler()
        self.is_trained = False
        self.feature_names = []
        
    def extract_team_features(self, team_stats: Dict) -> List[float]:
        """Extract numerical features from team statistics"""
        features = []
        
        # Basic stats (with defaults)
        features.append(team_stats.get('wins', 0))
        features.append(team_stats.get('losses', 0))
        features.append(team_stats.get('win_percentage', 0.5))
        features.append(team_stats.get('points_per_game', 0))
        features.append(team_stats.get('points_allowed_per_game', 0))
        features.append(team_stats.get('point_differential', 0))
        
        # Advanced stats
        features.append(team_stats.get('offensive_rating', 100))
        features.append(team_stats.get('defensive_rating', 100))
        features.append(team_stats.get('pace', 100))
        features.append(team_stats.get('home_record', 0.5))
        features.append(team_stats.get('away_record', 0.5))
        features.append(team_stats.get('recent_form', 0.5))  # Last 10 games
        
        return features
    
    def extract_matchup_features(self, matchup_data: Dict) -> List[float]:
        """Extract features from head-to-head matchup data"""
        features = []
        
        # Historical matchup
        features.append(matchup_data.get('head_to_head_wins', 0))
        features.append(matchup_data.get('head_to_head_losses', 0))
        features.append(matchup_data.get('avg_total_points', 0))
        features.append(matchup_data.get('avg_point_differential', 0))
        
        # Situational factors
        features.append(1 if matchup_data.get('is_home_game') else 0)
        features.append(1 if matchup_data.get('is_rivalry') else 0)
        features.append(matchup_data.get('rest_days_home', 1))
        features.append(matchup_data.get('rest_days_away', 1))
        
        return features
    
    def extract_betting_features(self, betting_data: Dict) -> List[float]:
        """Extract features from betting market data"""
        features = []
        
        # Market odds
        features.append(betting_data.get('spread', 0))
        features.append(betting_data.get('total', 0))
        features.append(betting_data.get('moneyline_home', 0))
        features.append(betting_data.get('moneyline_away', 0))
        
        # Market movement
        features.append(betting_data.get('spread_movement', 0))
        features.append(betting_data.get('total_movement', 0))
        features.append(betting_data.get('betting_volume', 0))
        features.append(betting_data.get('sharp_money_percentage', 50))
        
        return features
    
    def prepare_features(self, game_data: Dict) -> np.ndarray:
        """Convert game data to feature vector"""
        features = []
        
        # Team features
        home_team = game_data.get('home_team', {})
        away_team = game_data.get('away_team', {})
        
        features.extend(self.extract_team_features(home_team))
        features.extend(self.extract_team_features(away_team))
        
        # Matchup features
        matchup = game_data.get('matchup', {})
        features.extend(self.extract_matchup_features(matchup))
        
        # Betting features
        betting = game_data.get('betting', {})
        features.extend(self.extract_betting_features(betting))
        
        # Weather/external factors
        weather = game_data.get('weather', {})
        features.append(weather.get('temperature', 70))
        features.append(weather.get('wind_speed', 0))
        features.append(1 if weather.get('precipitation') else 0)
        
        return np.array(features).reshape(1, -1)
    
    def train(self, training_data: List[Dict]):
        """Train models on historical game data"""
        if not training_data:
            return
        
        X = []
        y_win = []
        y_spread = []
        y_total = []
        
        for game in training_data:
            features = self.prepare_features(game).flatten()
            X.append(features)
            
            # Outcomes
            result = game.get('result', {})
            y_win.append(1 if result.get('home_team_won') else 0)
            y_spread.append(1 if result.get('covered_spread') else 0)
            y_total.append(1 if result.get('went_over') else 0)
        
        X = np.array(X)
        X_scaled = self.scaler.fit_transform(X)
        
        # Train models
        self.win_model.fit(X_scaled, y_win)
        self.spread_model.fit(X_scaled, y_spread)
        self.total_model.fit(X_scaled, y_total)
        
        self.is_trained = True
    
    def predict_game_outcome(self, game_data: Dict) -> Dict[str, Tuple[int, float]]:
        """Predict multiple betting outcomes for a game"""
        if not self.is_trained:
            return {
                'win': (0, 0.5),
                'spread': (0, 0.5),
                'total': (0, 0.5)
            }
        
        features = self.prepare_features(game_data)
        features_scaled = self.scaler.transform(features)
        
        # Win prediction
        win_pred = self.win_model.predict(features_scaled)[0]
        win_prob = self.win_model.predict_proba(features_scaled)[0].max()
        
        # Spread prediction
        spread_pred = self.spread_model.predict(features_scaled)[0]
        spread_prob = self.spread_model.predict_proba(features_scaled)[0].max()
        
        # Total prediction
        total_pred = self.total_model.predict(features_scaled)[0]
        total_prob = self.total_model.predict_proba(features_scaled)[0].max()
        
        return {
            'win': (win_pred, win_prob),
            'spread': (spread_pred, spread_prob),
            'total': (total_pred, total_prob)
        }
    
    def calculate_bet_value(self, prediction: Tuple[int, float], odds: float) -> float:
        """Calculate expected value of a bet"""
        pred_outcome, confidence = prediction
        
        if pred_outcome == 1:  # Predict win
            implied_prob = 1 / (odds / 100 + 1) if odds > 0 else abs(odds) / (abs(odds) + 100)
            if confidence > implied_prob:
                return (confidence * odds - (1 - confidence) * 100) / 100
        
        return 0  # No value
    
    def update_model(self, game_data: Dict, actual_result: Dict):
        """Update model with new game result (incremental learning)"""
        if not self.is_trained:
            return
        
        # Store for batch retraining
        # In production, implement online learning or periodic retraining
        pass
    
    def get_model_performance(self) -> Dict:
        """Return model performance metrics"""
        if not self.is_trained:
            return {'status': 'not_trained'}
        
        return {
            'status': 'trained',
            'win_model_score': getattr(self.win_model, 'score_', 0),
            'spread_model_score': getattr(self.spread_model, 'score_', 0),
            'total_model_score': getattr(self.total_model, 'score_', 0),
            'last_updated': datetime.now().isoformat()
        }
