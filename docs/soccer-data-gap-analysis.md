# Soccer Data Gap Analysis & Solutions

## Current State: EPL Data Gaps

### What We Have (ESPN API - Free)
- ✅ Odds (The Odds API)
- ✅ Scores/Results (The Odds API)
- ✅ Schedules (The Odds API)
- ⚠️ **Limited Team Stats** (ESPN API):
  - Goal Difference
  - Total Goals
  - Assists
  - Goals Against
- ❌ No player stats
- ❌ No injury data
- ❌ No advanced metrics

### What We're Missing
- Possession %
- Shots on target
- Passing accuracy
- Corners
- Fouls
- Yellow/Red cards
- xG (Expected Goals)
- Player-level stats
- Injury reports
- Formation data
- Defensive stats

---

## Solution Options

### Option 1: SportMonks Football API ⭐ RECOMMENDED

**Free Plan:**
- ✅ **FREE FOREVER**
- ✅ 180 API calls per hour/endpoint
- ✅ Standard data features
- ❌ Only 4 leagues (Scottish Premiership, Danish Superliga, etc.)
- ❌ **Does NOT include EPL**

**14-Day Free Trial (All Plans):**
- Test full access to all leagues
- All data features
- No credit card required upfront

**Paid Plans (After Trial):**
Need to check pricing page for:
- European Plan (includes EPL, La Liga, Bundesliga, Serie A, Ligue 1)
- Worldwide Plan (111+ leagues)
- Custom Plan (select specific leagues)

**What You Get:**
- ✅ Possession stats
- ✅ Shots, shots on target
- ✅ Passing accuracy
- ✅ Corners, fouls, cards
- ✅ Player stats (goals, assists, minutes, etc.)
- ✅ xG data (add-on)
- ✅ Injury data
- ✅ Formation data
- ✅ Real-time updates

**Integration Effort:** Medium
- New API to integrate
- Different data structure than ESPN
- Need new collector: `sportmonks_collector.py`
- Estimated: 1-2 weeks

---

### Option 2: FootyStats API

**Pricing:**
- Not clearly listed (need to contact)
- Appears to be paid service

**Features:**
- Over/Under stats
- BTTS (Both Teams To Score)
- Corners, cards, goals
- Historical data

**Integration Effort:** Medium (1-2 weeks)

---

### Option 3: API-Football (RapidAPI)

**Pricing:**
- Free tier: Very limited
- Paid tiers: $10-$100+/month

**Features:**
- Comprehensive stats
- Player data
- Injuries
- Lineups

**Integration Effort:** Medium (1-2 weeks)

---

### Option 4: Keep ESPN + Add Specific Stats

**Approach:**
- Continue using ESPN for basic stats
- Scrape additional stats from public sources
- Use The Odds API for what they provide

**Pros:**
- Free
- No new API costs

**Cons:**
- Still missing most advanced stats
- Scraping is fragile
- May violate ToS
- High maintenance

**Integration Effort:** High (2-3 weeks, ongoing maintenance)

---

## Recommendation

### Phase 1: Test SportMonks (This Week)
1. **Sign up for 14-day free trial**
2. **Test EPL data quality**
   - Check what stats are available
   - Verify update frequency
   - Test API reliability
3. **Build proof-of-concept collector**
   - Create `sportmonks_collector.py`
   - Collect possession, shots, xG
   - Store in DynamoDB
4. **Evaluate cost vs value**
   - Check pricing after trial
   - Compare to current model performance
   - Decide if worth the cost

### Phase 2: Integrate if Valuable (Next 2 Weeks)
1. **Subscribe to appropriate plan**
   - Likely European Plan (EPL + top leagues)
   - Or Custom Plan (EPL only)
2. **Complete integration**
   - Finish collector implementation
   - Update models to use new stats
   - Add to EventBridge schedules
3. **Enhance models**
   - Add possession-based logic
   - Use xG for predictions
   - Incorporate shot data

### Phase 3: Expand to Other Leagues (Future)
- La Liga, Bundesliga, Serie A
- Same API, just different league IDs
- No additional integration work

---

## Cost-Benefit Analysis

### Current Situation
- **Cost:** $30/month (The Odds API only)
- **EPL Model Performance:** Unknown (need to backtest)
- **Data Quality:** Poor (only 4 basic stats)

### With SportMonks
- **Cost:** $30/month (The Odds API) + $X/month (SportMonks)
  - Need to check pricing page
  - Estimate: $50-100/month for European Plan
- **Expected Improvement:**
  - Better model accuracy (more data = better predictions)
  - Can build soccer-specific models
  - Player props for soccer
  - Competitive with other sports

### ROI Calculation
If SportMonks costs $70/month extra:
- Total: $100/month
- Need to improve EPL model by ~2-3% accuracy to justify
- Or attract more users with better soccer coverage
- Or enable soccer player props (new revenue stream)

---

## Alternative: Focus on Sports We Have Good Data For

### Current Strong Performers (from backtest)
- **NHL Matchup Model:** 68.6% accuracy, 31% ROI
- **EPL Matchup Model:** 69.2% accuracy, 32% ROI (despite limited data!)
- **NBA Momentum:** 57.5% accuracy, 9.77% ROI

### Strategy
1. **Keep EPL as-is** - It's actually performing well!
2. **Focus on improving NBA/NFL** - We have great data
3. **Add NCAA Basketball/Football** - Same data sources, zero cost
4. **Revisit soccer data later** - When we have more users/revenue

---

## Next Steps

### Immediate (Today)
1. ✅ Research soccer data sources (DONE)
2. ⏭️ **Decision:** Test SportMonks or focus elsewhere?

### If Testing SportMonks (This Week)
1. Sign up for 14-day free trial
2. Build proof-of-concept collector
3. Test data quality
4. Check pricing
5. Make go/no-go decision

### If Focusing Elsewhere (This Week)
1. Add NCAA Basketball (2 hours)
2. Add NCAA Football (1 hour)
3. Backtest current EPL model (30 min)
4. Improve models for sports with good data

---

## My Recommendation

**Focus on NCAA sports first, revisit soccer later.**

**Why:**
1. **EPL is already performing well** (69.2% accuracy!) despite limited data
2. **NCAA is zero-cost, zero-effort** - Same collectors, just add sport keys
3. **March Madness is coming** - Huge betting market
4. **Soccer data costs $50-100/month** - Hard to justify without more users
5. **Can always add SportMonks later** - 14-day trial available anytime

**When to revisit soccer:**
- When you have 1000+ active users
- When EPL model starts underperforming
- When users specifically request better soccer coverage
- When you have budget for additional APIs
