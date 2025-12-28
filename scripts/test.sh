#!/bin/bash

echo "🧪 Running Sports Betting Analytics Tests..."

cd backend

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found. Run ./scripts/start-api.sh first"
    exit 1
fi

# Install test dependencies if not already installed
pip install -r requirements-test.txt > /dev/null 2>&1

# Run tests
echo "Running API tests..."
cd ..
python -m pytest tests/ -v

echo ""
echo "🔍 Manual API Testing Commands:"
echo "Health Check:"
echo "  curl http://localhost:8000/health"
echo ""
echo "Create Prediction:"
echo "  curl -X POST 'http://localhost:8000/api/v1/predictions?event=Test%20Game&sport=football&data={}'"
echo ""
echo "Get Sports Data:"
echo "  curl 'http://localhost:8000/api/v1/sports-data?sport=football'"
