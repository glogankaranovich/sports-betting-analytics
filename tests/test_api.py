import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from api.main import app

client = TestClient(app)

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Sports Betting Analytics API"}

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data

def test_get_bets_endpoint():
    response = client.get("/api/v1/bets")
    assert response.status_code == 200
    assert response.json() == []

def test_create_prediction_endpoint():
    response = client.post("/api/v1/predictions", 
        params={"event": "Test Game", "sport": "football"},
        json={"data": {}}  # Send data as JSON body instead of params
    )
    assert response.status_code == 200
    data = response.json()
    assert data["event"] == "Test Game"
    assert data["sport"] == "football"
    assert "id" in data
    assert "probability" in data

def test_get_sports_data_endpoint():
    response = client.get("/api/v1/sports-data", params={
        "sport": "football"
    })
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert data["sport"] == "football"
