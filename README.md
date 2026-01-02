# Carpool Bets

AI-powered sports betting analytics with React frontend and AWS backend.

## 🚀 Current Status: Phase 3 Complete - ML Prediction Pipeline Operational

**✅ Completed Phases:**
- **Phase 1**: Data Collection (NFL/NBA games from The Odds API)
- **Phase 2**: React Frontend with API integration  
- **Phase 2.5**: AWS Cognito Authentication & API Security
- **Phase 2.6**: Professional UI/UX with filtering and responsive design
- **Phase 3.1**: ML Model Architecture Design
- **Phase 3.2**: Odds Analysis Engine Implementation
- **Phase 3.3**: Model Training Pipeline with Prediction Storage
- **Phase 3.4**: Prediction API Endpoints (/game-predictions, /prop-predictions)
- **Phase 3.5**: Frontend ML Integration with Tabbed Interface

**🔄 Next Phase**: AI Paper Trading System (Phase 5)

## Architecture

### 🎯 Production-Ready ML Platform
- **Backend API**: Lambda + API Gateway + DynamoDB with JWT authentication
- **ML Pipeline**: Consensus-based prediction models with scheduled generation
- **Frontend**: React TypeScript dashboard with 4-tab interface (Games, Game Predictions, Prop Predictions, Player Props)
- **Data Collection**: Automated odds collection from The Odds API (every 4 hours)
- **Prediction Generation**: ML models run every 6 hours with DynamoDB storage
- **CI/CD**: Full pipeline with dev/beta/prod environments + automatic rollback
- **Testing**: Comprehensive test suite with integration tests
- **Security**: Cognito User Pools with protected API endpoints

### 📊 Live ML-Powered Dashboard
- **25+ NFL/NBA games** with real-time odds from **8+ bookmakers**
- **AI Predictions**: Game outcomes and player prop predictions with confidence scores
- **Value Bet Detection**: ML-identified betting opportunities
- **Professional UI**: Tabbed interface with filtering, pagination, and responsive design
- **Authentication-protected** with test users in all environments
- **Real-time Updates**: Scheduled data collection and prediction generation

### 🤖 Machine Learning Features
- **Game Predictions**: Win probabilities using bookmaker consensus analysis
- **Player Props**: Statistical predictions for key player metrics
- **Confidence Scoring**: Model certainty ratings for each prediction
- **Value Bet Identification**: Opportunities where model disagrees with market
- **Historical Tracking**: Prediction storage with performance monitoring

### 🔐 Multi-Environment Authentication
- **Dev**: `testuser@example.com` / `TestPass123!`
- **Beta**: `testuser@example.com` / `TestPass123!`
- **Prod**: `testuser@example.com` / `TestPass123!`

## Getting Started

### Frontend Development
```bash
cd frontend
npm install
npm start  # Runs on http://localhost:3000
```

### Backend API
- **Dev**: https://pylcs4ypld.execute-api.us-east-1.amazonaws.com/prod
- **Beta**: https://fgguxgxr4b.execute-api.us-east-1.amazonaws.com/prod  
- **Prod**: https://rk6h0zryz5.execute-api.us-east-1.amazonaws.com/prod

### Infrastructure
```bash
cd infrastructure
make deploy-dev     # Deploy to dev environment
cdk deploy          # Deploy pipeline to all environments
```

## Deployment

### Branch Strategy
- **main**: Local development
- **beta**: Beta environment deployment
- **prod**: Production environment deployment

### Amplify Hosting
- Beta: https://beta.{amplify-domain}
- Prod: https://prod.{amplify-domain}

## Current Status

✅ **Phase 1**: Automated odds collection (Complete)  
✅ **Phase 2**: React frontend + API backend (Complete)  
🔄 **Phase 3**: AI prediction models (Next)

## API Endpoints

- `GET /health` - Health check
- `GET /games` - Get all games with odds
- `GET /sports` - Get available sports
- `GET /bookmakers` - Get available bookmakers

## Tech Stack

- **Frontend**: React TypeScript, Axios
- **Backend**: Python Lambda, API Gateway, DynamoDB
- **Infrastructure**: AWS CDK, CodePipeline
- **Hosting**: AWS Amplify
- **Data**: The Odds API

---

*Building the future of sports betting analytics, one bet at a time.*
