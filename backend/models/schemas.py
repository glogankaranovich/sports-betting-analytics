from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class BetStatus(str, Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"

class BetType(str, Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    OVER_UNDER = "over_under"

class InjuryStatus(str, Enum):
    HEALTHY = "healthy"
    QUESTIONABLE = "questionable"
    DOUBTFUL = "doubtful"
    OUT = "out"

class TeamStatsModel(BaseModel):
    """Team performance statistics for ML features."""
    team_id: str
    wins: int
    losses: int
    win_percentage: float
    points_per_game: float
    points_allowed_per_game: float
    home_record: str
    away_record: str
    last_5_games: str
    injuries_count: int

class PlayerInfoModel(BaseModel):
    """Key player information with injury status."""
    player_id: str
    name: str
    position: str
    injury_status: InjuryStatus
    season_stats: Dict[str, float]

class WeatherConditionsModel(BaseModel):
    """Weather conditions for outdoor games."""
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    wind_speed: Optional[float] = None
    precipitation: Optional[str] = None
    conditions: Optional[str] = None

class EnhancedSportsData(BaseModel):
    """Enhanced sports data with ML context."""
    id: Optional[str] = None
    event_id: str
    sport: str
    home_team: str
    away_team: str
    commence_time: datetime
    bookmaker_odds: List[Dict[str, Any]]
    source: str
    
    # Enhanced ML features
    home_team_stats: Optional[TeamStatsModel] = None
    away_team_stats: Optional[TeamStatsModel] = None
    key_players: List[PlayerInfoModel] = []
    weather: Optional[WeatherConditionsModel] = None
    referee_id: Optional[str] = None
    venue: Optional[str] = None
    
    collected_at: datetime

class BetStatus(str, Enum):
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"

class BetType(str, Enum):
    MONEYLINE = "moneyline"
    SPREAD = "spread"
    OVER_UNDER = "over_under"

class Bet(BaseModel):
    id: Optional[str] = None
    user_id: str
    sport: str
    event: str
    bet_type: BetType
    selection: str
    odds: float
    amount: float
    status: BetStatus = BetStatus.ACTIVE
    created_at: datetime
    settled_at: Optional[datetime] = None

class Prediction(BaseModel):
    id: Optional[str] = None
    event: str
    sport: str
    prediction: str
    probability: float
    confidence: float
    created_at: datetime
    
class SportsData(BaseModel):
    id: Optional[str] = None
    sport: str
    event: str
    data: dict
    source: str
    collected_at: datetime
