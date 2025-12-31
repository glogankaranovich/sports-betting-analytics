# Carpool Bets - Project Status

**Last Updated**: December 31, 2025  
**Progress**: Fresh Start - Two Service Architecture

## 🎯 Project Overview

**Carpool Bets** is being rebuilt as two distinct services:

### Service 1: Bet Information System
- **Data Collection**: Pull odds from The Odds API into DynamoDB
- **Rich Context**: Aggregate public opinion, weather, player stats, etc.
- **Data API**: Serve comprehensive bet information to frontend
- **Frontend**: Bet list + detailed bet view with all contextual data

### Service 2: AI Prediction Models (STARTING HERE)
- **ML Models**: Generate predictions (Model v1: odds-only, Model v2: +Reddit, etc.)
- **Recommendations**: AI-powered bet suggestions with confidence scores
- **Performance Tracking**: Historical backtesting with user bet amounts
- **Model Evolution**: Compare and improve model versions

## 🔄 Fresh Start Status

### What We Kept
- ✅ **Documentation**: All planning docs, research, and knowledge base
- ✅ **Repository Structure**: Clean directory organization
- ✅ **Vision**: Enhanced with two-service architecture and historical performance calculator

### What We Reset
- 🔄 **Backend**: Starting fresh with minimal FastAPI structure
- 🔄 **Frontend**: Clean React implementation focused on bet information
- 🔄 **Infrastructure**: Simplified AWS setup (DynamoDB + API Gateway, no Lambda complexity)

## 📋 Current TODO List

### ✅ Infrastructure Complete (NEW)
- [x] **Multi-environment CDK setup**: Dev, beta (staging), prod accounts with proper separation
- [x] **DynamoDB stack**: `carpool-bets-{env}` table with game_id/bookmaker keys  
- [x] **Pipeline stack**: Automated beta/prod deployment with GitHub integration
- [x] **Unit tests**: 5 tests passing for DynamoDB stack validation
- [x] **Makefile commands**: Easy deployment, testing, and monitoring
- [x] **Account cleanup**: Removed old stacks, clean slate achieved

### Phase 1: AI Prediction Models Service (CURRENT FOCUS)
- [ ] **Set up minimal project structure**
  - Clean backend/frontend/infrastructure directories ✅
  - Create simple FastAPI app for AI predictions
  - Basic React frontend for testing predictions

- [ ] **Build AI prediction models**
  - Model v1: Odds-only predictions using simple probability calculations
  - Model v2: Add Reddit sentiment analysis
  - Model v3: Progressive enhancement with additional data sources
  - Focus on generating predictions and recommendations

- [ ] **Historical performance tracking**
  - Track all AI recommendations with timestamps and outcomes
  - Calculate backtesting returns: "If you bet $X per recommendation, you would have made $Y"
  - Compare performance across model versions

### Phase 2: Bet Information System (FUTURE)
- [ ] **Odds API data collection**
- [ ] **Bet information API**
- [ ] **Rich context frontend**

## 🎯 Immediate Next Steps

1. **Start with AI Prediction Models Service**
   - Create minimal FastAPI backend for predictions
   - Implement Model v1 (odds-only predictions)
   - Build historical tracking system
   - Simple frontend to test predictions

2. **Focus on Core Value**
   - Generate actual predictions users can test
   - Track performance to build confidence
   - Prove the AI can make profitable recommendations

## 🛠️ Technical Approach

### Simplified Architecture
```
React Frontend → FastAPI Backend → DynamoDB
                      ↓
                AI Prediction Models
```

### Key Principles
- **Start Simple**: Focus on one service at a time
- **Prove Value**: Generate real predictions quickly
- **Track Performance**: Historical backtesting from day one
- **Iterate Fast**: No complex infrastructure to slow us down

## 📊 Success Metrics

### Phase 1 Goals
- [ ] **Model v1 Deployed**: Basic odds-only predictions working
- [ ] **Historical Tracking**: All recommendations stored with outcomes
- [ ] **Backtesting Calculator**: "You would have made $X" functionality
- [ ] **Performance Comparison**: Model v1 vs v2 vs v3 results

### Long-term Vision
- **50% Weekly ROI Target**: Ambitious but trackable goal
- **Multiple Model Versions**: Progressive enhancement approach
- **User Confidence**: Historical performance builds trust
- **Monetization Ready**: Premium "Carpool Model" vs custom models

## 🚀 Why This Approach Works

1. **Focused Scope**: One service at a time, no complexity overload
2. **Immediate Value**: Users can test AI predictions right away
3. **Confidence Building**: Historical performance tracking from start
4. **Scalable**: Can add Bet Information System later
5. **Clean Architecture**: Two services can evolve independently

---

**Current Focus**: AI Prediction Models Service  
**Next Milestone**: Model v1 generating real predictions  
**Repository**: https://github.com/glogankaranovich/sports-betting-analytics
