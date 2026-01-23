# Next Steps - January 22, 2026

## Immediate Priorities

### 1. Fix Prop Bet Verification Bug (High Priority)
**Issue**: All prop bet verifications returning False despite having player stats in database.

**Debug Steps**:
- [ ] Add detailed logging to outcome_collector._check_prop_analysis_accuracy()
- [ ] Verify player name matching between analyses and stats (case sensitivity, spacing)
- [ ] Check if sport parameter is correctly formatted (basketball_nba vs NBA)
- [ ] Test with a known completed game that has both prop analyses and player stats
- [ ] Verify stat field mapping (e.g., "assists" -> "AST")

**Files to Check**:
- `backend/outcome_collector.py` - prop verification logic
- `backend/player_stats_collector.py` - player stats storage format

### 2. Test Complete Outcome Verification Flow
Once tonight's games (Jan 22) complete:
- [ ] Run player_stats_collector Lambda for basketball_nba
- [ ] Verify player stats are stored correctly in DynamoDB
- [ ] Run outcome_collector Lambda
- [ ] Check that both game and prop analyses are verified
- [ ] Verify analytics dashboard shows updated metrics

**Commands**:
```bash
# Collect player stats
AWS_PROFILE=sports-betting-dev aws lambda invoke \
  --function-name Dev-PlayerStatsCollector-PlayerStatsCollectorFunct-BYO787NFkH42 \
  --payload '{"sport":"basketball_nba"}' \
  /tmp/player_stats_response.json

# Verify outcomes
AWS_PROFILE=sports-betting-dev aws lambda invoke \
  --function-name Dev-OutcomeCollector-OutcomeCollectorFunction3408B-nJ1mGv0BztIO \
  /tmp/outcome_response.json
```

### 3. Schedule Automated Collection
- [ ] Enable EventBridge schedules for automated data collection
- [ ] Schedule player_stats_collector to run 2 hours after games typically end
- [ ] Schedule outcome_collector to run 3 hours after games end
- [ ] Monitor CloudWatch logs for errors

## Medium-Term Enhancements

### 4. Improve Analytics Dashboard (1-2 days)
- [ ] Add date range filter for analytics
- [ ] Add sport filter to view performance by sport
- [ ] Add performance over time chart
- [ ] Add export functionality for analytics data
- [ ] Add refresh button to manually update data

### 5. Model Feedback Loop (2-3 weeks)
See `docs/model-feedback-loop-enhancement.md` for detailed plan:
- [ ] Phase 1: Dynamic confidence weighting based on recent performance
- [ ] Phase 2: Feature importance analysis
- [ ] Phase 3: Confidence calibration
- [ ] Phase 4: Automated model retraining

### 6. Additional Models (2-3 weeks)
Implement additional analysis models beyond consensus:
- [ ] Value-based model (identify odds discrepancies)
- [ ] Momentum model (recent team/player performance)
- [ ] Ensemble model (combine multiple models)

## Long-Term Goals

### 7. Parlay Builder (1-2 weeks)
- [ ] Identify correlated bets to avoid
- [ ] Calculate combined odds and probabilities
- [ ] Suggest optimal parlay combinations
- [ ] Track parlay performance

### 8. User Preferences & Tracking (1 week)
- [ ] Allow users to save favorite teams/players
- [ ] Track user's bet history (paper trading)
- [ ] Personalized recommendations based on preferences
- [ ] Performance tracking per user

### 9. Real-time Updates (1-2 weeks)
- [ ] WebSocket integration for live odds updates
- [ ] Real-time game scores
- [ ] Live analysis updates as odds change
- [ ] Push notifications for high-confidence bets

## Technical Debt

### 10. Testing & Quality
- [ ] Add unit tests for outcome verification logic
- [ ] Add integration tests for analytics endpoints
- [ ] Add E2E tests for frontend analytics dashboard
- [ ] Improve error handling and logging

### 11. Infrastructure Optimization
- [ ] Review Lambda timeout settings
- [ ] Optimize DynamoDB queries (add indexes if needed)
- [ ] Implement caching for frequently accessed data
- [ ] Set up CloudWatch alarms for failures

### 12. Documentation
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

**Last Updated**: January 22, 2026  
**Status**: Active Development  
**Current Focus**: Prop verification bug fix + Analytics dashboard
