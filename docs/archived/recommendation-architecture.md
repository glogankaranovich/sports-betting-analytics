# Recommendation Architecture

## Per-Bookmaker Predictions

Predictions are generated separately for each bookmaker to enable practical recommendations.

### Rationale
- Users bet at specific bookmakers, not across multiple ones
- Recommendations must specify WHERE to place the bet
- Each bookmaker has different odds and availability

### Implementation
- **One prediction per game per bookmaker**
- Each prediction contains odds from only that bookmaker
- Recommendations specify the exact bookmaker and odds

### Example
Instead of:
```
"Best bet: Lakers -210 (theoretical best odds)"
```

We generate:
```
"Bet Lakers -240 at FanDuel" 
"Bet Lakers -235 at DraftKings"
"Bet Lakers -250 at BetMGM"
```

### Data Structure
```json
{
  "pk": "PRED#GAME#123#fanduel",
  "bookmaker": "fanduel", 
  "odds_data": [
    {"team": "Lakers", "price": -240},
    {"team": "Grizzlies", "price": 198}
  ]
}
```

This enables actionable recommendations that users can immediately execute.
