# Test Coverage Plan

**Current Coverage**: 74.9%  
**Target Coverage**: 80%+  
**Status**: 818 tests passing

## Priority Modules (0% Coverage - Critical)

### P0: Handler Functions (0% coverage)
1. **elo_handler.py** (0%, 14 lines)
   - Tests needed: ELO calculation, rating updates
   - Estimated: 30 min

2. **per_handler.py** (0%, 15 lines)
   - Tests needed: PER calculation
   - Estimated: 30 min

3. **metrics_calculator_handler.py** (0%, 22 lines)
   - Tests needed: Metrics calculation logic
   - Estimated: 45 min

4. **email_forwarder.py** (0%, 28 lines)
   - Tests needed: Email forwarding logic, SES integration
   - Estimated: 45 min

5. **notification_processor.py** (0%, 32 lines)
   - Tests needed: Notification processing, filtering
   - Estimated: 1 hour

6. **notification_service.py** (0%, 59 lines)
   - Tests needed: Notification creation, delivery
   - Estimated: 1.5 hours

**P0 Total**: ~5 hours

## Priority Modules (< 50% Coverage - High)

### P1: Core Business Logic

7. **benny_weekly_reporter.py** (14.2%, 103 missing)
   - Tests needed: Template rendering, email data preparation, subscriber queries
   - Estimated: 2 hours

8. **user_model_weight_adjuster.py** (14.3%, 78 missing)
   - Tests needed: Weight adjustment logic, learning algorithm
   - Estimated: 2 hours

9. **api/user.py** (21.1%, 75 missing)
   - Tests needed: Profile CRUD, preferences, subscription management
   - Estimated: 2 hours

10. **api/analyses.py** (30.8%, 54 missing)
    - Tests needed: Analysis queries, filtering, aggregation
    - Estimated: 1.5 hours

11. **api/misc.py** (37.8%, 28 missing)
    - Tests needed: Misc endpoints (health, stats, etc.)
    - Estimated: 1 hour

12. **travel_fatigue_calculator.py** (39.1%, 56 missing)
    - Tests needed: Distance calculation, fatigue scoring
    - Estimated: 1.5 hours

13. **compliance_logger.py** (43.5%, 35 missing)
    - Tests needed: Logging logic, compliance checks
    - Estimated: 1 hour

14. **team_stats_collector.py** (43.5%, 210 missing)
    - Tests needed: Stats collection, API integration, data transformation
    - Estimated: 3 hours

15. **dao.py** (47.1%, 63 missing)
    - Tests needed: DynamoDB operations, queries, error handling
    - Estimated: 2 hours

16. **odds_collector.py** (47.5%, 138 missing)
    - Tests needed: Odds API integration, data parsing, storage
    - Estimated: 2.5 hours

17. **ml/model_factory.py** (48.9%, 24 missing)
    - Tests needed: Model instantiation, configuration
    - Estimated: 1 hour

18. **ai_agent.py** (49.1%, 117 missing)
    - Tests needed: AI conversation, prompt generation, response parsing
    - Estimated: 2.5 hours

**P1 Total**: ~24 hours

## Priority Modules (50-80% Coverage - Medium)

### P2: Supporting Logic

19. **custom_data.py** (50.6%, 39 missing)
    - Tests needed: Custom data CRUD, validation
    - Estimated: 1 hour

20. **ml/models/player_stats.py** (51.4%, 67 missing)
    - Tests needed: Player stats model logic, predictions
    - Estimated: 2 hours

**P2 Total**: ~3 hours

## Implementation Plan

### Phase 1: Quick Wins (P0 - 5 hours)
Focus on 0% coverage handlers - small files, big impact on coverage percentage.

**Order**:
1. elo_handler.py
2. per_handler.py
3. metrics_calculator_handler.py
4. email_forwarder.py
5. notification_processor.py
6. notification_service.py

**Expected coverage gain**: +2-3%

### Phase 2: Core Business Logic (P1 - 24 hours)
Focus on critical business logic with most missing lines.

**Order by impact**:
1. team_stats_collector.py (210 lines)
2. odds_collector.py (138 lines)
3. ai_agent.py (117 lines)
4. benny_weekly_reporter.py (103 lines)
5. user_model_weight_adjuster.py (78 lines)
6. api/user.py (75 lines)
7. dao.py (63 lines)
8. travel_fatigue_calculator.py (56 lines)
9. api/analyses.py (54 missing)
10. compliance_logger.py (35 lines)
11. api/misc.py (28 lines)
12. ml/model_factory.py (24 lines)

**Expected coverage gain**: +8-10%

### Phase 3: Polish (P2 - 3 hours)
Bring remaining modules to 80%+.

**Expected coverage gain**: +1-2%

## Total Effort

- **P0 (Quick Wins)**: 5 hours → 77-78% coverage
- **P1 (Core Logic)**: 24 hours → 85-88% coverage
- **P2 (Polish)**: 3 hours → 86-90% coverage

**Total**: 32 hours to reach 80%+ coverage

## Success Criteria

- [ ] Overall coverage ≥ 80%
- [ ] All P0 modules ≥ 80% coverage
- [ ] All P1 modules ≥ 70% coverage
- [ ] No critical business logic < 50% coverage
- [ ] All tests passing
- [ ] Integration tests updated for new code

## Notes

- Integration tests currently have 25 errors - need investigation
- Focus on unit tests for business logic, not integration tests
- Mock external dependencies (DynamoDB, SES, APIs)
- Test edge cases and error handling
- Document test scenarios in docstrings
