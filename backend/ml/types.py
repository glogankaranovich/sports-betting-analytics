"""Shared types for ML models"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class AnalysisResult:
    """Standardized analysis result for DynamoDB storage"""

    game_id: str
    model: str
    analysis_type: str  # "game" or "prop"
    sport: str
    prediction: str
    confidence: float
    reasoning: str
    home_team: str = None
    away_team: str = None
    commence_time: str = None
    player_name: str = None
    bookmaker: str = None
    market_key: str = None  # For props: player_points, player_assists, etc.
    recommended_odds: int = None  # American odds for ROI calculation

    @property
    def roi(self) -> float:
        """Calculate expected ROI"""
        if not self.recommended_odds:
            return None
        odds = self.recommended_odds
        roi_multiplier = 100 / abs(odds) if odds < 0 else odds / 100
        return round(
            (self.confidence * roi_multiplier - (1 - self.confidence)) * 100, 1
        )

    @property
    def risk_level(self) -> str:
        """Determine risk level based on confidence"""
        if self.confidence >= 0.65:
            return "conservative"
        elif self.confidence >= 0.55:
            return "moderate"
        else:
            return "aggressive"

    @property
    def implied_probability(self) -> float:
        """Calculate implied probability from odds"""
        if not self.recommended_odds:
            return None
        odds = self.recommended_odds
        implied_prob = abs(odds) / (abs(odds) + 100) if odds < 0 else 100 / (odds + 100)
        return round(implied_prob * 100, 1)

    def to_dynamodb_item(self) -> Dict[str, Any]:
        """Convert to DynamoDB item format with GSI attributes"""
        if self.analysis_type == "prop" and self.player_name:
            pk = f"ANALYSIS#{self.sport}#{self.game_id}#{self.player_name}#{self.bookmaker}"
            analysis_pk = f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#prop"
            analysis_time_pk = f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#prop"
        else:
            pk = f"ANALYSIS#{self.sport}#{self.game_id}#{self.bookmaker}"
            analysis_pk = f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#game"
            analysis_time_pk = f"ANALYSIS#{self.sport}#{self.bookmaker}#{self.model}#game"

        item = {
            "pk": pk,
            "sk": f"{self.model}#{self.analysis_type}#LATEST",
            "analysis_pk": analysis_pk,
            "analysis_time_pk": analysis_time_pk,
            "model_type": f"{self.model}#{self.analysis_type}",
            "analysis_type": self.analysis_type,
            "model": self.model,
            "game_id": self.game_id,
            "sport": self.sport,
            "bookmaker": self.bookmaker,
            "home_team": self.home_team,
            "away_team": self.away_team,
            "player_name": self.player_name,
            "market_key": self.market_key,
            "prediction": self.prediction,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "recommended_odds": self.recommended_odds,
            "roi": self.roi,
            "risk_level": self.risk_level,
            "implied_probability": self.implied_probability,
            "created_at": datetime.utcnow().isoformat(),
            "latest": True,
        }
        
        if self.commence_time:
            item["commence_time"] = self.commence_time
        else:
            item["commence_time"] = "9999-12-31T23:59:59Z"
        
        return item
