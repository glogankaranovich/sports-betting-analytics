# Carpool Bets

AI-powered sports betting analytics with historical performance tracking.

## Architecture

Two distinct services working together:

### 🤖 AI Prediction Models (Current Focus)
- Generate predictions using multiple model versions
- Track historical performance for backtesting
- Calculate returns: "If you bet $X per recommendation, you would have made $Y"

### 📊 Bet Information System (Future)
- Collect odds data from The Odds API
- Aggregate context: public opinion, weather, player stats
- Rich frontend for detailed bet analysis

## Getting Started

```bash
# Clone the repository
git clone https://github.com/glogankaranovich/sports-betting-analytics.git
cd sports-betting-analytics

# Start with AI Prediction Models service
cd backend
# Setup instructions coming soon
```

## Current Status

🔄 **Fresh Start**: Building AI Prediction Models service first  
📈 **Goal**: 50% weekly ROI through AI recommendations  
📊 **Approach**: Start simple, prove value, iterate fast

## Model Versions

- **Model v1**: Odds-only predictions (simple probability calculations)
- **Model v2**: Odds + Reddit sentiment analysis  
- **Model v3**: Progressive enhancement with additional data sources

## Key Features

- **Historical Backtesting**: See what you would have made following AI recommendations
- **Model Comparison**: Track performance across different model versions
- **Performance Tracking**: All AI recommendations stored with outcomes
- **Confidence Scoring**: AI provides confidence levels for each prediction

---

*Building the future of sports betting analytics, one prediction at a time.*
