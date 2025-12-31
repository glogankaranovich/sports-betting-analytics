# Carpool Bets

AI-powered sports betting analytics with React frontend and AWS backend.

## Architecture

### 🎯 Current MVP (Phase 2 Complete!)
- **Backend API**: Lambda + API Gateway + DynamoDB
- **Frontend**: React TypeScript dashboard with Amplify hosting
- **Data Collection**: Automated odds collection from The Odds API
- **CI/CD**: Full pipeline with dev/beta/prod environments

### 📊 Live Betting Dashboard
- Real-time odds from multiple bookmakers (BetMGM, FanDuel, DraftKings, etc.)
- NFL and NBA games with moneyline, spreads, and totals
- Environment-specific deployments (dev/beta/prod)

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
