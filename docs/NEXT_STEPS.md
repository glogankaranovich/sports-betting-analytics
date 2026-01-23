# Next Steps - January 23, 2026

## Recently Completed ✅

### ~~1. Fix Prop Bet Verification Bug~~ (COMPLETED)
**Issue**: All prop bet verifications returning False despite having player stats in database.

**Solution**: Fixed `_map_sport_name()` function in outcome_collector.py that was converting "basketball_nba" to "NBA", causing player stats lookup to fail. Changed to keep sport names consistent.

**Results**: Prop verification now working correctly - successfully finding player stats and verifying prop bet accuracy.

### ~~2. Fix Unit Tests~~ (COMPLETED)
**Issue**: 5 newly created unit tests failing due to mismatched implementations.

**Solution**: 
- Fixed player_stats_collector tests: no constructor params, uses env var
- Fixed team_stats_collector tests: returns dict not list
- Fixed model_analytics tests: correct method names and return structure
- Fixed outcome_collector test: _map_sport_name returns api_sport directly
- Fixed odds_collector lambda_handler test: requires sport parameter

**Results**: All 50 unit tests now passing (9 test files, 50 test cases).

## Immediate Priorities

### 1. Schedule Automated Data Collection (High Priority)
**Status**: Infrastructure ready, schedules need to be enabled

**Current Schedule**:
- 6:00 PM ET: Odds collection (NBA/NFL season-aware)
- 7:00 PM ET: Game analysis generation
- 7:05 PM ET: Prop analysis generation
- 8:00 PM ET: Game insight generation
- 8:05 PM ET: Prop insight generation
- 2:00 AM ET: Player/team stats collection
- 3:00 AM ET: Outcome verification

**Commands**:
```bash
# Test player stats collection
AWS_PROFILE=sports-betting-dev aws lambda invoke \
  --function-name Dev-PlayerStatsCollector-PlayerStatsCollectorFunct-BYO787NFkH42 \
  --payload '{"sport":"basketball_nba"}' \
  /tmp/player_stats_response.json

# Test outcome verification
AWS_PROFILE=sports-betting-dev aws lambda invoke \
  --function-name Dev-OutcomeCollector-OutcomeCollectorFunction3408B-nJ1mGv0BztIO \
  /tmp/outcome_response.json
```

**Tasks**:
- [ ] Enable EventBridge schedules in infrastructure code
- [ ] Deploy to dev environment
- [ ] Monitor first automated run
- [ ] Verify data collection pipeline end-to-end

## Medium-Term Enhancements

### 2. Improve Analytics Dashboard (1-2 days)
- [ ] Add date range filter for analytics
- [ ] Add sport filter to view performance by sport
- [ ] Add performance over time chart
- [ ] Add export functionality for analytics data
- [ ] Add refresh button to manually update data

### 3. Model Feedback Loop (2-3 weeks)
See `docs/model-feedback-loop-enhancement.md` for detailed plan:
- [ ] Phase 1: Dynamic confidence weighting based on recent performance
- [ ] Phase 2: Feature importance analysis
- [ ] Phase 3: Confidence calibration
- [ ] Phase 4: Automated model retraining

### 4. Additional Models (2-3 weeks)
Implement additional analysis models beyond consensus:
- [ ] Value-based model (identify odds discrepancies)
- [ ] Momentum model (recent team/player performance)
- [ ] Ensemble model (combine multiple models)

## Long-Term Goals

### 5. Parlay Builder (1-2 weeks)
- [ ] Identify correlated bets to avoid
- [ ] Calculate combined odds and probabilities
- [ ] Suggest optimal parlay combinations
- [ ] Track parlay performance

### 6. User Preferences & Tracking (1 week)
- [ ] Allow users to save favorite teams/players
- [ ] Track user's bet history (paper trading)
- [ ] Personalized recommendations based on preferences
- [ ] Performance tracking per user

### 7. Real-time Updates (1-2 weeks)
- [ ] WebSocket integration for live odds updates
- [ ] Real-time game scores
- [ ] Live analysis updates as odds change
- [ ] Push notifications for high-confidence bets

## Technical Debt

### 8. Testing & Quality
- [x] Add unit tests for player_stats_collector (5 tests)
- [x] Add unit tests for team_stats_collector (5 tests)
- [x] Add unit tests for model_analytics (3 tests)
- [x] Add unit tests for analysis_generator (5 tests)
- [x] Add unit tests for insight_generator (6 tests)
- [ ] Add unit tests for outcome verification logic
- [ ] Add integration tests for analytics endpoints
- [ ] Add E2E tests for frontend analytics dashboard
- [ ] Improve error handling and logging

### 9. Infrastructure Optimization
- [ ] Review Lambda timeout settings
- [ ] Optimize DynamoDB queries (add indexes if needed)
- [ ] Implement caching for frequently accessed data
- [ ] Set up CloudWatch alarms for failures

### 10. Documentation
- [ ] Update API documentation with analytics endpoints
- [ ] Document data collection workflow
- [ ] Create troubleshooting guide
- [ ] Add architecture diagrams

## Monitoring & Maintenance

### Daily
- [ ] Check CloudWatch logs for errors
- [ ] Verify data collection is running
- [ ] Monitor API response times

### Weekly
- [ ] Review analytics for model performance trends
- [ ] Check for data quality issues
- [ ] Review and address any user feedback

### Monthly
- [ ] Review and optimize AWS costs
- [ ] Update dependencies and security patches
- [ ] Review and update documentation
- [ ] Plan next month's enhancements

---

**Last Updated**: January 23, 2026  
**Status**: Active Development  
**Current Focus**: Unit test fixes complete - all 50 tests passing
