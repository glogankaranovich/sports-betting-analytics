# Carpool Bets

AI-powered sports betting analytics with React frontend and AWS backend.

## 🚀 Current Status: Phase 2.6 Complete

**✅ Completed Phases:**
- **Phase 1**: Data Collection (100+ NFL games from The Odds API)
- **Phase 2**: React Frontend with API integration  
- **Phase 2.5**: AWS Cognito Authentication & API Security
- **Phase 2.6**: Professional UI/UX with filtering and responsive design

**🔄 Next Phase**: AI/ML Model Development (Phase 3-4)

## Architecture

### 🎯 Production-Ready MVP
- **Backend API**: Lambda + API Gateway + DynamoDB with JWT authentication
- **Frontend**: React TypeScript dashboard with AWS Amplify authentication
- **Data Collection**: Automated odds collection from The Odds API (every 4 hours)
- **CI/CD**: Full pipeline with dev/beta/prod environments + automatic rollback
- **Testing**: 13 frontend tests + comprehensive integration tests
- **Security**: Cognito User Pools with protected API endpoints

### 📊 Live Betting Dashboard
- **100+ NFL games** with real-time odds from **11 bookmakers**
- Professional UI with sport/bookmaker filtering
- Responsive design with modern glassmorphism styling
- Authentication-protected with test users in all environments
- Game grouping by matchup with multiple bookmaker odds comparison

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
