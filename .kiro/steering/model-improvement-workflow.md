# Model Improvement Workflow

## 🎯 Overview

This document outlines the data-driven process for improving prediction models and validating changes before deployment.

## 📊 Core Principle

**Never deploy model changes without backtesting validation.**

All model improvements must show measurable improvement in:
- Accuracy (% correct predictions)
- ROI (return on investment)
- Sharpe Ratio (risk-adjusted returns)

## 🚀 Recent Success: Player Stats Model

**Deployed:** February 26, 2026  
**Performance:** 53.7% accuracy, -2% ROI (nearly profitable)  
**Improvement:** +12.5% accuracy, +19.32% ROI vs baseline  
**Documentation:** [Player Stats Model Deployment](../../docs/player-stats-model-deployment.md)

This model demonstrates the workflow in action:
1. Identified prop betting as losing money (-21% to -100% ROI)
2. Created new model using player historical stats
3. Backtested and validated improvement
4. Integrated data sources (stats, news, injuries)
5. Deployed to production with EventBridge schedules

## 🔄 Step-by-Step Workflow

### 1. Identify Improvement Opportunity

**Review backtest results to find opportunities:**

```bash
# Run comprehensive backtest for a sport
AWS_PROFILE=sports-betting-dev python3 scripts/backtest_models.py dev \
  --compare --sport basketball_nba --days 90 > docs/backtest-nba-90d.md

# Test multiple sports
for sport in basketball_nba icehockey_nhl soccer_epl; do
  AWS_PROFILE=sports-betting-dev python3 scripts/backtest_models.py dev \
    --compare --sport $sport --days 90 > docs/backtest-${sport}-90d.md
done

# Review results
cat docs/backtest-nba-90d.md
```

**Look for:**
- ❌ Models with <50% accuracy or negative ROI
- ✅ Models with high accuracy but could be improved
- 🔍 Sport-specific performance differences
- 📉 Prop betting performance (typically underperforms)

**Example findings:**
```
momentum             game        57.5%      9.77%      0.10    120  ✅ Good
contrarian           game        40.0%    -23.64%     -0.25    120  ❌ Bad
matchup              game        45.8%    -12.50%     -0.13    120  ❌ Bad (NBA)
matchup              game        68.6%     31.02%      0.35     51  ✅ Great (NHL)
```

### 2. Analyze Why Model Fails/Succeeds

**Check model implementation:**

```bash
# Find the model class
grep -n "class ContrarianModel" backend/ml/models.py

# Read the implementation
cat backend/ml/models.py | sed -n '753,850p'
```

**Common issues:**
- Using unreliable signals (e.g., guessing at "sharp action")
- Not validating with actual data (e.g., Elo ratings, player stats)
- Overfitting to specific scenarios
- Ignoring sport-specific factors

**Example analysis:**
```
Contrarian model fails because:
- Assumes line movement = sharp action (not always true)
- Could be injury news, weather, or public betting
- No way to distinguish signal from noise
```

### 3. Design Improvement

**Types of improvements:**

#### A. Fix Broken Logic
```python
# Before: Guessing at sharp action
if abs(movement) > 1.0:
    confidence = 0.75  # Arbitrary

# After: Validate with Elo ratings
if abs(movement) > 1.0 and elo_confirms:
    confidence = 0.75
else:
    return None  # Skip if not validated
```

#### B. Add New Data Sources
```python
# Add player stats for prop betting
player_stats = get_player_stats(player_name, last_n_games=20)
recent_avg = calculate_average(player_stats, market_type)
confidence = calculate_confidence(line, recent_avg, opponent)
```

#### C. Sport-Specific Tuning
```python
# Different logic per sport
if sport == 'icehockey_nhl':
    # Matchups matter more in hockey
    weight_matchup_history = 0.7
elif sport == 'basketball_nba':
    # Rest matters more in basketball
    weight_rest_days = 0.7
```

#### D. Add New Models
```python
class PaceModel(BaseAnalysisModel):
    """Predict based on game tempo and possessions"""
    
    def analyze_game_odds(self, game_id, odds_items, game_info):
        # Calculate expected possessions
        # Compare to total line
        # Return prediction
```

### 4. Implement Changes

**Make minimal, focused changes:**

```bash
# Edit the model
vim backend/ml/models.py

# Or create new model file
vim backend/ml/pace_model.py
```

**Best practices:**
- Change one thing at a time
- Add logging to understand behavior
- Keep old logic commented for comparison
- Document why the change was made

### 5. Backtest the Changes

**Test locally before deploying:**

```bash
# Backtest specific model
AWS_PROFILE=sports-betting-dev python3 scripts/backtest_models.py dev \
  --model contrarian --sport basketball_nba --days 90

# Compare all models (includes your changes)
AWS_PROFILE=sports-betting-dev python3 scripts/backtest_models.py dev \
  --compare --sport basketball_nba --days 90
```

**Validate improvement:**
```
Before: contrarian - 40.0% accuracy, -23.64% ROI
After:  contrarian - 52.0% accuracy, +2.15% ROI  ✅ Improved!
```

**If worse, iterate:**
- Revert changes
- Try different approach
- Add more validation
- Test on different time periods

### 6. Test Dynamic Weighting

**Verify ensemble automatically uses improved model:**

```bash
# Check weights before/after
AWS_PROFILE=sports-betting-dev python3 << 'EOF'
import sys
sys.path.insert(0, 'backend')
from ml.dynamic_weighting import DynamicModelWeighting

weighting = DynamicModelWeighting(lookback_days=90)
weights = weighting.get_model_weights('basketball_nba', 'game')

for model, weight in sorted(weights.items(), key=lambda x: x[1], reverse=True):
    if weight > 0.01:
        print(f"{model:20s}: {weight*100:5.1f}%")
EOF
```

**Expected result:**
```
Before: contrarian gets 0% weight (negative ROI)
After:  contrarian gets 8.5% weight (positive ROI)
```

### 7. Document Results

**Save backtest results:**

```bash
# Save to docs for reference
AWS_PROFILE=sports-betting-dev python3 scripts/backtest_models.py dev \
  --compare --sport basketball_nba --days 90 > docs/backtest-nba-after-contrarian-fix.md

# Add summary to commit message
git add backend/ml/models.py docs/backtest-nba-after-contrarian-fix.md
```

**Document in commit:**
```bash
git commit -m "feat: improve contrarian model with Elo validation

Backtest results (90 days, NBA):
- Before: 40.0% accuracy, -23.64% ROI
- After: 52.0% accuracy, +2.15% ROI
- Improvement: +12.0% accuracy, +25.79% ROI

Changes:
- Added Elo rating validation for line movement
- Only bet when Elo confirms contrarian signal
- Skip bets when Elo disagrees with line movement

See docs/backtest-nba-after-contrarian-fix.md for full results"
```

### 8. Deploy and Monitor

**Deploy to dev first:**

```bash
cd infrastructure
make deploy-dev
```

**Monitor live performance:**

```bash
# Check if new predictions are being made
AWS_PROFILE=sports-betting-dev aws dynamodb query \
  --table-name carpool-bets-v2-dev \
  --index-name VerifiedAnalysisGSI \
  --key-condition-expression "verified_analysis_pk = :pk" \
  --expression-attribute-values '{":pk":{"S":"VERIFIED#contrarian#basketball_nba#game"}}' \
  --limit 5

# Check ensemble weights in production
# (weights update automatically based on new performance)
```

**After 1-2 weeks, re-backtest:**
```bash
# Verify improvement holds with new data
AWS_PROFILE=sports-betting-dev python3 scripts/backtest_models.py dev \
  --model contrarian --sport basketball_nba --days 30
```

### 9. Push to Production

**If dev performance is good:**

```bash
# Commit and push (triggers pipeline)
git push origin main

# Monitor pipeline
make check-pipeline

# Verify in staging/prod
# (automatic through pipeline)
```

## 🆕 Adding New Models

### Step 1: Create Model Class

```python
# backend/ml/models.py or backend/ml/new_model.py

class NewModel(BaseAnalysisModel):
    """Brief description of model strategy"""
    
    def __init__(self):
        super().__init__()
        # Initialize any dependencies
    
    def analyze_game_odds(self, game_id: str, odds_items: List[Dict], 
                          game_info: Dict) -> AnalysisResult:
        """Analyze game odds and return prediction"""
        try:
            # Your logic here
            
            return AnalysisResult(
                game_id=game_id,
                model="new_model",
                analysis_type="game",
                sport=game_info.get("sport"),
                home_team=game_info.get("home_team"),
                away_team=game_info.get("away_team"),
                commence_time=game_info.get("commence_time"),
                prediction="Team +7.5",
                confidence=0.75,
                reasoning="Why this prediction makes sense",
                recommended_odds=-110,
            )
        except Exception as e:
            logger.error(f"Error in new_model: {e}")
            return None
    
    def analyze_prop_odds(self, prop_item: Dict) -> AnalysisResult:
        """Analyze prop odds (optional)"""
        return None  # Or implement prop logic
```

### Step 2: Register Model

```python
# backend/ml/models.py - in EnsembleModel.__init__

self.models = {
    "value": ValueModel(),
    "momentum": MomentumModel(),
    "new_model": NewModel(),  # Add here
    # ... other models
}
```

### Step 3: Generate Predictions

**Run prediction generator to create historical predictions:**

```bash
# This will analyze all recent games with your new model
AWS_PROFILE=sports-betting-dev aws lambda invoke \
  --function-name Dev-PredictionGenerator-PredictionGeneratorFunctio-XXX \
  --payload '{"sport":"basketball_nba","model":"new_model","bet_type":"game"}' \
  /tmp/response.json
```

### Step 4: Wait for Outcomes

**Predictions need to be verified before backtesting:**
- Games must complete
- Outcome collector must run
- Typically wait 1-2 days for enough data

### Step 5: Backtest New Model

```bash
# Once you have 20+ verified predictions
AWS_PROFILE=sports-betting-dev python3 scripts/backtest_models.py dev \
  --model new_model --sport basketball_nba --days 90
```

### Step 6: Compare to Existing Models

```bash
# See where it ranks
AWS_PROFILE=sports-betting-dev python3 scripts/backtest_models.py dev \
  --compare --sport basketball_nba --days 90 | grep new_model
```

**Decision criteria:**
- ✅ Deploy if: Accuracy >52% AND ROI >2%
- 🔄 Iterate if: Close but not quite there
- ❌ Disable if: Accuracy <50% OR ROI <0%

## 📈 Performance Metrics Explained

### Accuracy
- **What**: Percentage of correct predictions
- **Good**: >52% (beats -110 odds breakeven of 52.4%)
- **Great**: >55%
- **Excellent**: >60%

### ROI (Return on Investment)
- **What**: Profit divided by amount wagered
- **Good**: >2%
- **Great**: >5%
- **Excellent**: >10%

### Sharpe Ratio
- **What**: Risk-adjusted returns (avg return / std deviation)
- **Good**: >0.05
- **Great**: >0.10
- **Excellent**: >0.20

### Max Drawdown
- **What**: Largest peak-to-trough decline
- **Good**: <$2,000 (on $10k bankroll)
- **Great**: <$1,000
- **Excellent**: <$500

## 🚨 Common Pitfalls

### 1. Overfitting to Historical Data
❌ **Bad**: "This pattern worked perfectly in the last 10 games"
✅ **Good**: "This pattern has 55% accuracy over 120 games across 3 months"

### 2. Not Enough Data
❌ **Bad**: Backtesting on 10 games
✅ **Good**: Minimum 50 games, ideally 100+

### 3. Ignoring Sport Differences
❌ **Bad**: Same logic for all sports
✅ **Good**: Sport-specific tuning and validation

### 4. Deploying Without Validation
❌ **Bad**: "This should work" → deploy
✅ **Good**: Backtest → validate → deploy → monitor

### 5. Not Monitoring Live Performance
❌ **Bad**: Deploy and forget
✅ **Good**: Re-backtest monthly, check live accuracy

## 🎓 Learning from Results

### When Model Performs Well
**Document why:**
- What signal is it capturing?
- What data sources does it use?
- What makes it reliable?
- Can we apply this to other sports?

### When Model Performs Poorly
**Analyze failure:**
- What assumptions were wrong?
- What data is missing?
- Is the signal too noisy?
- Should we disable or fix?

### Sport-Specific Insights
**Track what works per sport:**
- **NBA**: Rest days, momentum, pace
- **NHL**: Matchups (69% accuracy!), goalie performance, divisional games
- **EPL (Soccer)**: Matchups (69% accuracy!), team styles, home advantage
- **NFL**: Weather, injuries, home field advantage
- **MLB**: Pitcher matchups, ballpark factors, weather

**Current best models by sport (90-day backtest):**

| Sport | Best Model | Accuracy | ROI | Notes |
|-------|------------|----------|-----|-------|
| NBA | Momentum | 57.5% | 9.77% | Line movement + rest |
| NBA | Rest Schedule | 57.5% | 9.77% | Back-to-back games |
| NHL | Matchup | 68.6% | 31.02% | Head-to-head history |
| NHL | Rest Schedule | 60.8% | 16.04% | Travel fatigue |
| EPL | Matchup | 69.2% | 32.17% | Team styles matter |
| EPL | Ensemble | 64.5% | 23.17% | Weighted combination |

## 📚 Resources

### Backtest Scripts
- `scripts/backtest_models.py` - Main backtesting tool
- `scripts/simulate_ensemble.py` - Test ensemble weighting

### Model Files
- `backend/ml/models.py` - All model implementations
- `backend/ml/dynamic_weighting.py` - Ensemble weighting logic

### Documentation
- `docs/backtest-*.md` - Historical backtest results
- `.kiro/steering/development-workflow.md` - General dev workflow
- `.kiro/steering/model-improvement-workflow.md` - This document

---

*Created: 2026-02-26*  
*Purpose: Ensure all model changes are data-driven and validated*  
*Next: Apply this workflow to improve prop betting models*
