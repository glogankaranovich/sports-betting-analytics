# Sports Betting Analytics System

A comprehensive system for analyzing sports data and making informed betting decisions using machine learning.

## 🚀 Multi-Account Pipeline Active

This project uses automated deployment pipeline:
- **Dev**: Manual deployment for development/testing
- **Staging**: Automated deployment + integration tests  
- **Production**: Automated deployment if staging tests pass

## Features

- **Data Collection**: Web crawler/scraper for sports statistics and betting data
- **Bet Management**: Track active bets and outcomes
- **ML Predictions**: Probability-based betting recommendations
- **Learning System**: Feedback loop to improve predictions
- **Web Interface**: User-friendly dashboard for managing bets and viewing analytics

## Architecture

- **Backend**: FastAPI with modular components
- **Data Storage**: AWS DynamoDB for structured data, S3 for raw data
- **ML Engine**: Custom prediction models with probability calculations
- **Frontend**: React web application
- **Infrastructure**: AWS multi-account setup with automated pipeline

## Quick Commands

```bash
# Deploy to dev environment
make deploy-dev

# Deploy pipeline (staging/prod automation)  
make deploy-pipeline

# Run all tests
make test

# Start development server
make dev
```

## Project Structure

```
├── backend/
│   ├── api/          # FastAPI application
│   ├── crawler/      # Data collection modules
│   ├── ml/           # Machine learning models
│   ├── models/       # Data models
│   └── utils/        # Utility functions
├── frontend/
│   ├── src/          # React application
│   └── public/       # Static assets
├── infrastructure/   # AWS CloudFormation/CDK
├── docs/            # Documentation
├── tests/           # Test suites
└── scripts/         # Deployment and utility scripts
```

## Getting Started

1. Clone the repository
2. Set up backend dependencies: `cd backend && pip install -r requirements.txt`
3. Set up frontend dependencies: `cd frontend && npm install`
4. Configure AWS credentials
5. Deploy infrastructure: `cd infrastructure && cdk deploy`
6. Start development servers

## Development

- Backend API: `uvicorn backend.api.main:app --reload`
- Frontend: `cd frontend && npm start`

## License

MIT License
