# Data Collection Assessment - January 25, 2026

## Current Data Collection

### ✅ What We're Collecting:

1. **Odds Data** (`odds_collector.py`)
   - Game odds (moneyline, spreads, totals)
   - Player props (points, rebounds, assists, etc.)
   - Multiple bookmakers
   - Real-time updates

2. **Game Outcomes** (`outcome_collector.py`)
   - Final scores
   - Bet settlement (win/loss)
   - ROI tracking

3. **Player Stats** (`player_stats_collector.py`)
   - Post-game player statistics
   - From ESPN API
   - NBA, NFL, MLB, NHL

4. **Team Stats** (`team_stats_collector.py`)
   - Team performance metrics
   - From ESPN API
   - All major sports

5. **Schedule Data** (`schedule_collector.py`)
   - Upcoming games
   - Rest days
   - Back-to-back games

6. **Injury Reports** (`injury_collector.py`)
   - Player injury status
   - Injury type/location
   - Return dates
   - From ESPN API

---

## Model Data Requirements Analysis

### Consensus Model ✅
**Needs**: Odds from multiple bookmakers
**Have**: ✅ Yes (odds_collector)
**Status**: Complete

### Value Model ✅
**Needs**: Odds discrepancies across bookmakers
**Have**: ✅ Yes (odds_collector)
**Status**: Complete

### Momentum Model ⚠️
**Needs**: Historical odds over time (line movement)
**Have**: ❌ Only current odds (no historical tracking)
**Gap**: Need to store odds at multiple timestamps
**Impact**: Model uses simplified version

### Contrarian Model ⚠️
**Needs**: Public betting percentages, line movement
**Have**: ❌ No public betting data
**Gap**: Would need paid API (Action Network, etc.)
**Impact**: Model infers from line movement only

### Hot/Cold Model ✅
**Needs**: Recent game outcomes
**Have**: ✅ Yes (outcome_collector)
**Status**: Complete

### Rest/Schedule Model ✅
**Needs**: Schedule, rest days, back-to-backs
**Have**: ✅ Yes (schedule_collector)
**Status**: Complete

### Matchup Model ⚠️
**Needs**: Head-to-head history, team stats
**Have**: ✅ Team stats, ❌ No H2H history
**Gap**: Need to store historical game results with matchup info
**Impact**: Model uses team stats only, no true H2H

### Injury-Aware Model ✅
**Needs**: Injury reports
**Have**: ✅ Yes (injury_collector)
**Status**: Complete (but needs team ID mapping fix)

---

## Data Gaps & Recommendations

### 🔴 Critical Gaps (Blocking Model Effectiveness)

**1. Historical Odds (for Momentum Model)**
- **What**: Store odds at multiple timestamps (e.g., opening line, -24h, -12h, -1h, current)
- **Why**: Track line movement and sharp action
- **Effort**: Medium - modify odds_collector to store historical snapshots
- **Priority**: HIGH - Momentum model currently simplified

**2. Head-to-Head History (for Matchup Model)**
- **What**: Store game results with team matchup info
- **Why**: Analyze historical performance between specific teams
- **Effort**: Low - enhance outcome_collector to tag matchups
- **Priority**: MEDIUM - Model works but not optimal

### 🟡 Nice-to-Have Gaps (Would Improve Models)

**3. Public Betting Percentages**
- **What**: % of bets on each side
- **Why**: Better contrarian signals
- **Cost**: $50-200/month (Action Network, Sports Insights)
- **Priority**: LOW - Model works without it

**4. Weather Data (for outdoor sports)**
- **What**: Temperature, wind, precipitation
- **Why**: Affects NFL, MLB, EPL games
- **Effort**: Low - free weather APIs available
- **Priority**: LOW - Minor impact

**5. Player Usage/Importance Metrics**
- **What**: Minutes played, usage rate, starter status
- **Why**: Weight injuries by player importance
- **Effort**: Low - available in player stats
- **Priority**: MEDIUM - Would improve injury model

**6. Venue/Travel Data**
- **What**: Stadium info, travel distance
- **Why**: Home/away advantage, travel fatigue
- **Effort**: Low - static data
- **Priority**: LOW - Rest/Schedule model covers most of this

### ✅ Data We Don't Need

- ❌ Social media sentiment (too noisy)
- ❌ News articles (hard to parse reliably)
- ❌ Advanced analytics (PER, DVOA) - nice but not critical
- ❌ Referee data - minimal impact

---

## Recommendations

### Option 1: Ship Now (Minimal Fixes)
**Add:**
- Nothing new
**Fix:**
- Team ID mappings (injury model)
- Player injury lookup (injury model)
- Merge analysis/insight generators

**Timeline**: 3-5 days
**Quality**: Good enough for beta launch

### Option 2: Add Critical Gaps (Recommended)
**Add:**
1. Historical odds tracking (for Momentum)
2. H2H history tagging (for Matchup)
3. Player importance metrics (for Injury)

**Fix:**
- All Option 1 fixes

**Timeline**: 1-2 weeks
**Quality**: Production-ready

### Option 3: Add Everything
**Add:**
- All Option 2 items
- Public betting percentages (paid)
- Weather data
- Venue/travel data

**Timeline**: 3-4 weeks
**Quality**: Best-in-class

---

## My Recommendation: **Option 2**

**Why:**
- Historical odds and H2H history are **critical** for model effectiveness
- Player importance is **easy** to add (already in stats)
- Public betting data is **expensive** and not critical
- Weather/venue are **nice-to-have** but low ROI

**What to Add:**

1. **Historical Odds Tracking** (2-3 days)
   - Modify odds_collector to store snapshots
   - Store: opening line, -24h, -12h, current
   - Enable true line movement analysis

2. **H2H History** (1 day)
   - Enhance outcome_collector to tag matchups
   - Query format: `H2H#NBA#Lakers#Celtics`
   - Enable historical matchup analysis

3. **Player Importance** (1 day)
   - Add starter flag, minutes, usage rate to player stats
   - Weight injury impact by importance
   - Already available in ESPN API

**Total Effort**: 4-5 days
**Result**: All models work at full effectiveness

---

## Bottom Line

**Current State**: You have 80% of the data you need.

**Missing 20%**:
- Historical odds (critical for Momentum)
- H2H history (important for Matchup)
- Player importance (nice for Injury)

**Recommendation**: Add the missing 20% before public launch. It's only 4-5 days of work and makes a big difference in model quality.

**After that**: You're good. Don't need more data collection for now.
