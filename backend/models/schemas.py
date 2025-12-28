from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
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
