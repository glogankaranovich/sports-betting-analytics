# ML Model Architecture

## Overview
Multi-model ensemble approach with incremental development phases, starting simple and adding complexity based on performance validation.

## Development Phases

### Phase 3: Model v1 - Odds-Only Baseline
**Input Features:**
- Current betting odds from multiple bookmakers
- Line movement patterns and velocity
- Odds consensus and variance across books
- Opening vs current line differences
- Market efficiency indicators

**Output:** Win probability, value bet identification
**Goal:** Establish baseline performance using only market data

### Phase 4: Model v2 - Multi-Platform Sentiment Integration
**Additional Input Features:**
- **Discord**: Real-time community discussions from sports betting servers
- **Twitter/X**: Sentiment from sports analysts, journalists, and fan accounts
- **Reddit**: In-depth analysis from sports betting and team-specific subreddits
- Social media volume and engagement metrics
- Public vs contrarian sentiment indicators

**Output:** Sentiment-adjusted win probability, public bias detection
**Goal:** Improve accuracy by incorporating comprehensive social sentiment

### Phase 5: Model v3 - Enhanced Context (Future)
**Additional Input Features:**
- Team performance metrics and recent form
- Injury reports and player availability
- Weather conditions (outdoor sports)
- Referee historical patterns
- Head-to-head matchup history

**Output:** Context-aware predictions with confidence intervals
**Goal:** Maximum accuracy through comprehensive data integration

## Specialized Models (Future Architecture)

### 1. Market Movement Model (Phase 3)
**Input Features:**
- Opening vs current lines
- Line movement velocity
- Sharp vs public money indicators
- Betting volume patterns
- Cross-sportsbook line comparison

**Output:** Market efficiency signals, value bet identification

### 2. Multi-Platform Sentiment Model (Phase 4)
**Input Features:**
- **Discord Servers:**
  - Sports betting communities (r/sportsbook equivalent)
  - Team-specific Discord servers
  - Real-time game discussion sentiment
- **Twitter/X:**
  - Sports analyst tweets and predictions
  - Breaking news sentiment impact
  - Fan engagement and buzz metrics
- **Reddit:**
  - Sports betting subreddits (r/sportsbook, r/sportsbetting)
  - Team subreddits (r/nfl, r/nba team subs)
  - Expert analysis and discussion threads

**Output:** Contrarian betting signals, public bias indicators

### 3. Team Performance Model (Phase 5)
**Input Features:**
- Historical win/loss records
- Point differentials and recent form
- Home/away performance splits
- Injury reports and player availability
- Rest days between games
- Head-to-head matchup history

**Output:** Win probability, point spread prediction

### 4. Referee Bias Model (Phase 5)
**Input Features:**
- Referee historical call patterns
- Home team favoritism metrics
- Over/under call tendencies
- Foul call frequency by referee
- Game flow impact (close vs blowout games)

**Output:** Bias-adjusted win probability, total points adjustment

## Meta-Model (Ensemble) - Phase 6+

### Architecture
- Takes predictions from all specialized models as input
- Learns optimal weighting for each model by game type/situation
- Handles conflicting signals between models
- Outputs final win probability and confidence intervals

### Weighting Strategy
- Dynamic weights based on:
  - Historical model performance
  - Game context (playoff vs regular season)
  - Data availability and quality
  - Model confidence scores

## Implementation Strategy

### Incremental Development
1. **Phase 3**: Build and validate odds-only model
2. **Phase 4**: Add multi-platform sentiment, compare performance
3. **Phase 5+**: Gradually add complexity based on ROI improvement

### Performance Validation
- Each phase must demonstrate improved ROI over previous version
- A/B testing between model versions
- Rollback capability if new features decrease performance

### Data Sources by Phase
- **Phase 3**: The Odds API (already implemented)
- **Phase 4**: Discord API, Twitter API, Reddit API
- **Phase 5**: ESPN API, weather APIs, referee databases

## Performance Metrics

### Model Evaluation
- Accuracy (win/loss predictions)
- Calibration (predicted probabilities vs actual outcomes)
- ROI on recommended bets
- Sharpe ratio of betting strategy

### Phase Comparison
- Performance improvement over previous phase
- Statistical significance of improvements
- Cost-benefit analysis of additional data sources
