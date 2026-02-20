"""
Elo rating calculator for team strength assessment
"""
import os
import boto3
from datetime import datetime
from typing import Dict, Optional, Tuple
from decimal import Decimal

class EloCalculator:
    def __init__(self):
        self.table = boto3.resource('dynamodb').Table(os.environ['DYNAMODB_TABLE'])
        self.k_factor = 32  # Standard K-factor
        self.initial_rating = 1500
    
    def get_team_rating(self, sport: str, team_name: str) -> float:
        """Get current Elo rating for a team"""
        normalized_name = team_name.strip().replace(" ", "_").upper()
        
        response = self.table.query(
            KeyConditionExpression="pk = :pk AND begins_with(sk, :sk_prefix)",
            ExpressionAttributeValues={
                ":pk": f"ELO#{sport}#{normalized_name}",
                ":sk_prefix": "2"
            },
            ScanIndexForward=False,
            Limit=1
        )
        
        items = response.get("Items", [])
        if items:
            return float(items[0].get("rating", self.initial_rating))
        return self.initial_rating
    
    def calculate_expected_score(self, rating_a: float, rating_b: float) -> float:
        """Calculate expected score for team A"""
        return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    
    def update_ratings(self, sport: str, home_team: str, away_team: str, 
                      home_score: int, away_score: int) -> Tuple[float, float]:
        """Update Elo ratings after a game"""
        home_rating = self.get_team_rating(sport, home_team)
        away_rating = self.get_team_rating(sport, away_team)
        
        # Calculate expected scores
        home_expected = self.calculate_expected_score(home_rating, away_rating)
        away_expected = 1 - home_expected
        
        # Actual scores (1 for win, 0.5 for tie, 0 for loss)
        if home_score > away_score:
            home_actual, away_actual = 1.0, 0.0
        elif away_score > home_score:
            home_actual, away_actual = 0.0, 1.0
        else:
            home_actual, away_actual = 0.5, 0.5
        
        # Calculate new ratings
        new_home_rating = home_rating + self.k_factor * (home_actual - home_expected)
        new_away_rating = away_rating + self.k_factor * (away_actual - away_expected)
        
        # Store new ratings
        timestamp = datetime.utcnow().isoformat()
        self._store_rating(sport, home_team, new_home_rating, timestamp)
        self._store_rating(sport, away_team, new_away_rating, timestamp)
        
        return new_home_rating, new_away_rating
    
    def _store_rating(self, sport: str, team_name: str, rating: float, timestamp: str):
        """Store Elo rating in DynamoDB"""
        normalized_name = team_name.strip().replace(" ", "_").upper()
        
        self.table.put_item(Item={
            "pk": f"ELO#{sport}#{normalized_name}",
            "sk": timestamp,
            "sport": sport,
            "team_name": team_name,
            "rating": Decimal(str(round(rating, 2))),
            "updated_at": timestamp
        })
    
    def process_game_result(self, game_data: Dict) -> Optional[Tuple[float, float]]:
        """Process a completed game and update Elo ratings"""
        sport = game_data.get("sport")
        status = game_data.get("status", {})
        
        if not status.get("type", {}).get("completed"):
            return None
        
        competitions = game_data.get("competitions", [{}])[0]
        competitors = competitions.get("competitors", [])
        
        if len(competitors) != 2:
            return None
        
        home_team = competitors[0].get("team", {}).get("displayName")
        away_team = competitors[1].get("team", {}).get("displayName")
        home_score = int(competitors[0].get("score", 0))
        away_score = int(competitors[1].get("score", 0))
        
        return self.update_ratings(sport, home_team, away_team, home_score, away_score)
