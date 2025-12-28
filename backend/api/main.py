from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import List, Optional
import uuid
import sys
import os

# Add backend to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.schemas import Bet, Prediction, SportsData, BetStatus

app = FastAPI(title="Sports Betting Analytics API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Sports Betting Analytics API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow()}

# Bets endpoints
@app.get("/api/v1/bets", response_model=List[Bet])
async def get_bets():
    # TODO: Implement database query
    return []

@app.post("/api/v1/bets", response_model=Bet)
async def create_bet(bet: Bet):
    bet.id = str(uuid.uuid4())
    bet.user_id = "test-user"  # Temporary for testing
    bet.created_at = datetime.utcnow()
    # TODO: Save to database
    return bet

@app.put("/api/v1/bets/{bet_id}/outcome")
async def update_bet_outcome(bet_id: str, status: BetStatus):
    # TODO: Update bet in database
    return {"message": "Bet updated", "bet_id": bet_id, "status": status}

# Predictions endpoints
@app.get("/api/v1/predictions", response_model=List[Prediction])
async def get_predictions(sport: Optional[str] = None, date: Optional[str] = None):
    # TODO: Query predictions from database
    return []

@app.post("/api/v1/predictions", response_model=Prediction)
async def create_prediction(event: str, sport: str, data: dict):
    # TODO: Generate prediction using ML engine
    prediction = Prediction(
        id=str(uuid.uuid4()),
        event=event,
        sport=sport,
        prediction="placeholder",
        probability=0.5,
        confidence=0.5,
        created_at=datetime.utcnow()
    )
    return prediction

# Sports data endpoints
@app.get("/api/v1/sports-data")
async def get_sports_data(sport: Optional[str] = None, date: Optional[str] = None):
    # TODO: Query sports data from database
    return {"data": [], "sport": sport, "date": date}
