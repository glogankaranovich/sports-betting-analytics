# Benny (Sports Betting) Audit - Data-Driven Analysis

**Audit Date:** March 7, 2026  
**Auditor:** Kiro AI  
**Focus:** "Let data guide decisions" principle

---

## Executive Summary

**Verdict: ✅ Benny IS data-driven, but needs more data to validate effectiveness**

Benny has a solid learning framework in place, but it's unclear if there's enough historical data to make meaningful adjustments. The system is well-architected for learning, but may be premature in some optimizations.

---

## What Benny Does Right ✅

### 1. **Learning Loop Exists**
- Tracks all bets with outcomes in DynamoDB
- Calculates win rate, ROI, performance by sport/market
- Adjusts confidence thresholds based on results
- Passes historical performance to AI in every decision

**Code Evidence:**
```python
def update_learning_parameters(self):
    # Get last 30 days of settled bets
    # Calculate win rate, ROI
    # Adjust MIN_CONFIDENCE based on performance
    # Track performance by sport and market
```

### 2. **AI Gets Historical Context**
Every bet decision includes:
```
BENNY'S HISTORICAL PERFORMANCE (Last 30 days):
Overall: 60% win rate, 12% ROI (25 bets)
By Sport: NFL: 8/12 (67%), NBA: 7/13 (54%)
By Market: spreads: 10/15 (67%), player_points: 5/10 (50%)
```

Plus:
- What's working (winning patterns)
- What's not working (losing patterns)
- Recent mistakes
- Recent wins
- Winning factors

**This is excellent** - AI sees past performance and learns.

### 3. **Dynamic Threshold Adjustment**
```python
if win_rate > 0.60:
    adjustment = -0.02  # Lower threshold (more bets)
elif win_rate < 0.45:
    adjustment = 0.05   # Raise threshold (fewer bets)
```

**This is data-driven** - System adapts based on results.

### 4. **Kelly Criterion for Position Sizing**
Uses Kelly formula based on:
- Confidence (from AI)
- Odds (from market)
- Historical win rate

**This is mathematically optimal** - Not arbitrary bet sizing.

---

## Potential Issues ⚠️

### 1. **Insufficient Data for Learning**
```python
if len(bets) < 10:  # Need at least 10 bets to learn
    return
```

**Question:** How many bets has Benny actually placed?
- Need 50+ bets for statistical significance
- Need 100+ for reliable sport/market breakdowns
- Current threshold (10 bets) is too low

**Recommendation:** 
- Check actual bet count in production
- If < 50 bets, disable learning adjustments
- Focus on data collection first

### 2. **Premature Optimization**
System tracks:
- Performance by sport
- Performance by market
- Performance by prop market
- Winning factors
- Recent mistakes
- What works / what fails

**Question:** With how much data?
- If only 20-30 bets total, these breakdowns are noise
- "NBA player_points: 2/3 wins" is not statistically meaningful
- Could lead to overfitting

**Recommendation:**
- Require minimum sample size per category (e.g., 20 bets)
- Don't show/use categories with insufficient data
- Add confidence intervals to win rates

### 3. **No A/B Testing**
System adjusts thresholds based on performance, but:
- No control group to compare against
- Can't isolate what changes actually helped
- Adjustments could be random noise

**Recommendation:**
- Track "what would have happened" with old thresholds
- Compare adjusted vs baseline performance
- Only keep changes that show improvement

### 4. **ROI Calculation May Be Misleading**
```python
total_deposits = self._get_total_deposits()
true_profit = self.bankroll - self.WEEKLY_BUDGET - total_deposits
```

**Question:** Is this accounting for:
- Vig/juice (sportsbooks take 10% on losses)
- Variance (short-term luck vs long-term edge)
- Sample size (20 bets at 60% win rate could be luck)

**Recommendation:**
- Calculate ROI after vig
- Show confidence intervals (e.g., "12% ROI ± 8%")
- Require 100+ bets before claiming profitability

### 5. **Confidence Threshold Adjustments Too Aggressive**
```python
if win_rate > 0.60:
    adjustment = -0.02  # Lower by 2%
elif win_rate < 0.45:
    adjustment = 0.05   # Raise by 5%
```

**Issue:** 
- 60% win rate with 20 bets could be luck (expected range: 45-75%)
- Lowering threshold after lucky streak = more risk
- Raising threshold after unlucky streak = missing opportunities

**Recommendation:**
- Use statistical significance tests
- Only adjust if p-value < 0.05
- Smaller adjustments (0.5% instead of 2-5%)

---

## Critical Questions to Answer

### 1. **How many bets has Benny placed?**
- Total bets: ?
- Settled bets (won/lost): ?
- By sport: NFL ?, NBA ?, etc.
- By market: spreads ?, player props ?, etc.

**Action:** Query DynamoDB for actual counts

### 2. **What's the actual performance?**
- Overall win rate: ?
- Overall ROI (after vig): ?
- By sport (with sample sizes): ?
- By market (with sample sizes): ?

**Action:** Run performance report

### 3. **Is the learning helping?**
- Performance before adjustments: ?
- Performance after adjustments: ?
- Statistical significance: ?

**Action:** Compare periods before/after learning enabled

### 4. **Are thresholds optimal?**
- Current: 65% confidence, 5% EV
- Actual results at these thresholds: ?
- Would different thresholds be better: ?

**Action:** Backtest different thresholds

---

## Recommendations by Priority

### Immediate (Do Now)

1. **Check actual bet counts**
   ```bash
   # Query DynamoDB for BENNY bets
   # Count total, by sport, by market
   # Determine if enough data exists
   ```

2. **Add minimum sample size checks**
   ```python
   MIN_BETS_FOR_LEARNING = 50
   MIN_BETS_PER_CATEGORY = 20
   
   if len(bets) < MIN_BETS_FOR_LEARNING:
       print("Insufficient data for learning")
       return  # Don't adjust thresholds yet
   ```

3. **Add confidence intervals to metrics**
   ```python
   # Show: "60% win rate (95% CI: 45-75%)"
   # Don't claim significance without proof
   ```

### Short-term (After 50+ bets)

4. **Implement statistical significance tests**
   ```python
   from scipy.stats import binomtest
   
   # Only adjust if performance is statistically significant
   p_value = binomtest(wins, total, 0.5).pvalue
   if p_value < 0.05:
       # Adjustment is justified
   ```

5. **Add A/B testing framework**
   ```python
   # Track what would have happened with baseline
   # Compare adjusted vs baseline
   # Only keep changes that improve performance
   ```

6. **Calculate proper ROI after vig**
   ```python
   # Account for -110 odds (10% vig)
   # Show true profitability
   ```

### Long-term (After 100+ bets)

7. **Backtest threshold optimization**
   - Test different confidence levels (60%, 65%, 70%)
   - Test different EV requirements (3%, 5%, 7%)
   - Find optimal balance of volume vs quality

8. **Add variance analysis**
   - Calculate expected variance
   - Determine if results are within normal range
   - Avoid overreacting to short-term luck

9. **Implement Bayesian updating**
   - Start with prior beliefs
   - Update based on evidence
   - More robust than simple threshold adjustments

---

## Comparison to Trading Agent

| Feature | Benny (Sports Betting) | Trading Agent (Options) |
|---------|------------------------|-------------------------|
| **Learning loop** | ✅ Implemented | ❌ Not yet (planned Phase 8) |
| **Historical context to AI** | ✅ Yes | ❌ Not yet |
| **Dynamic thresholds** | ✅ Yes | ❌ Fixed (70%, 2:1) |
| **Data-driven decisions** | ⚠️ Yes, but may lack data | ✅ Will be after 30 days |
| **Statistical rigor** | ⚠️ Needs improvement | N/A (not implemented yet) |
| **A/B testing** | ❌ No | ❌ No |

**Key difference:** Benny has learning infrastructure but may be using it prematurely. Trading agent is waiting for data before implementing learning.

---

## Final Verdict

**Benny is well-architected for data-driven decisions, but:**

1. ✅ **Learning framework is solid** - Code is good
2. ⚠️ **May lack sufficient data** - Need to verify bet counts
3. ⚠️ **Statistical rigor needs improvement** - Add significance tests
4. ⚠️ **Risk of overfitting** - Too many categories with small samples
5. ✅ **Better than trading agent** - Already has learning loop

**Recommended approach:**
1. Check actual bet counts (if < 50, disable learning)
2. Add minimum sample size requirements
3. Add statistical significance tests
4. Focus on data collection until 100+ bets
5. Then optimize based on proven patterns

**You didn't go down the wrong route** - The architecture is good. Just need to ensure you have enough data before trusting the adjustments.

---

## Action Items

**For you to do:**
1. Query DynamoDB: How many Benny bets exist?
2. Run performance report: What's the actual win rate/ROI?
3. Check if learning adjustments have been made
4. Determine if sample size is sufficient

**For me to implement (if needed):**
1. Add minimum sample size checks
2. Add confidence intervals to metrics
3. Implement statistical significance tests
4. Add A/B testing framework

**Want me to check the actual data and implement improvements?**
