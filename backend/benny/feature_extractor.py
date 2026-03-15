"""Feature extraction for bet analysis"""
from typing import Dict, Any, Optional
from decimal import Decimal


class FeatureExtractor:
    """Extract structured features from bet context for learning"""
    
    @staticmethod
    def extract_features(
        game_data: Dict[str, Any],
        home_elo: float,
        away_elo: float,
        fatigue: Dict[str, Any],
        home_injuries: list,
        away_injuries: list,
        home_form: Dict[str, Any],
        away_form: Dict[str, Any],
        weather: Dict[str, Any],
        h2h_history: list,
        odds: float,
        market_key: str,
        prediction: str
    ) -> Dict[str, Any]:
        """Extract features from bet context"""
        
        # Elo difference
        elo_diff = home_elo - away_elo
        
        # Fatigue scores
        home_fatigue = fatigue.get("home_fatigue_score", 0) if fatigue else 0
        away_fatigue = fatigue.get("away_fatigue_score", 0) if fatigue else 0
        fatigue_advantage = away_fatigue - home_fatigue
        
        # Injury impact (count of key injuries)
        home_injury_count = len([i for i in home_injuries if i.get("impact") in ["high", "medium"]])
        away_injury_count = len([i for i in away_injuries if i.get("impact") in ["high", "medium"]])
        injury_advantage = away_injury_count - home_injury_count
        
        # Form streak
        home_streak = FeatureExtractor._parse_streak(home_form.get("streak", ""))
        away_streak = FeatureExtractor._parse_streak(away_form.get("streak", ""))
        form_advantage = home_streak - away_streak
        
        # Weather impact
        weather_impact = weather.get("impact_level", "none") if weather else "none"
        weather_score = {"high": 3, "moderate": 2, "low": 1, "none": 0}.get(weather_impact, 0)
        
        # H2H record
        h2h_wins = 0
        h2h_total = len(h2h_history) if h2h_history else 0
        if h2h_history:
            home_team = game_data.get("home_team")
            for game in h2h_history:
                if game.get("winner") == home_team:
                    h2h_wins += 1
        h2h_win_rate = h2h_wins / h2h_total if h2h_total > 0 else 0.5
        
        # Odds value (implied probability vs confidence)
        implied_prob = FeatureExtractor._odds_to_probability(odds)
        
        # Home advantage (always 1 for home team bets, 0 for away)
        is_home_bet = game_data.get("home_team", "").lower() in prediction.lower()
        
        return {
            "elo_diff": Decimal(str(elo_diff)),
            "elo_favorite": Decimal(str(max(home_elo, away_elo))),
            "fatigue_score": Decimal(str(home_fatigue if is_home_bet else away_fatigue)),
            "fatigue_advantage": Decimal(str(fatigue_advantage if is_home_bet else -fatigue_advantage)),
            "injury_count": home_injury_count if is_home_bet else away_injury_count,
            "injury_advantage": Decimal(str(injury_advantage if is_home_bet else -injury_advantage)),
            "form_streak": home_streak if is_home_bet else away_streak,
            "form_advantage": Decimal(str(form_advantage if is_home_bet else -form_advantage)),
            "weather_impact": weather_score,
            "h2h_win_rate": Decimal(str(h2h_win_rate if is_home_bet else 1 - h2h_win_rate)),
            "implied_probability": Decimal(str(implied_prob)),
            "is_home": is_home_bet,
            "is_favorite": (home_elo > away_elo) == is_home_bet,
            "market_type": market_key,
            "sport": game_data.get("sport", ""),
        }
    
    @staticmethod
    def _parse_streak(streak_str: str) -> int:
        """Parse streak string like 'W3' or 'L2' into signed integer"""
        if not streak_str:
            return 0
        streak_str = streak_str.strip().upper()
        if streak_str.startswith("W"):
            return int(streak_str[1:]) if len(streak_str) > 1 else 1
        elif streak_str.startswith("L"):
            return -int(streak_str[1:]) if len(streak_str) > 1 else -1
        return 0
    
    @staticmethod
    def _odds_to_probability(odds: float) -> float:
        """Convert American odds to implied probability"""
        if odds > 0:
            return 100 / (odds + 100)
        else:
            return abs(odds) / (abs(odds) + 100)
