#!/bin/bash

echo "🚀 Starting Sports Betting Analytics API..."

# Check if we're in the right directory
if [ ! -f "backend/api/main.py" ]; then
    echo "❌ Error: Run this from the project root directory"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "backend/venv" ]; then
    echo "📦 Creating virtual environment..."
    cd backend
    python3 -m venv venv
    cd ..
fi

# Activate virtual environment and install dependencies
echo "📦 Installing dependencies..."
cd backend
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-test.txt

# Start the API server
echo "🌐 Starting FastAPI server on http://localhost:8000"
echo "📖 API docs available at http://localhost:8000/docs"
echo "🔍 Health check: http://localhost:8000/health"
echo ""
echo "Press Ctrl+C to stop the server"

uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
