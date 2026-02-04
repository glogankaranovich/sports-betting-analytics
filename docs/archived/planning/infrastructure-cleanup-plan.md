# Infrastructure Cleanup Plan

## Current State Analysis

### Deployed Stacks (Active)
- `PredictionGeneratorStack` - Lambda function generating predictions
- `RecommendationGeneratorStack` - Lambda function generating recommendations
- Both stacks are currently deployed and consuming resources

### Backend Code (To Remove)
- `backend/prediction_generator.py` - Main prediction logic
- `backend/prediction_tracker.py` - Prediction storage and tracking
- `backend/recommendation_generator.py` - Recommendation logic
- `backend/recommendation_storage.py` - Recommendation storage
- `backend/bet_recommendations.py` - Bet recommendation utilities

### Infrastructure Code (To Remove)
- `infrastructure/lib/prediction-generator-stack.ts` - CDK stack definition
- `infrastructure/lib/recommendation-generator-stack.ts` - CDK stack definition

### Tests (To Remove)
- `backend/tests/unit/test_prediction_tracker.py`
- `backend/tests/unit/test_recommendation_generator.py`
- `backend/tests/unit/test_recommendation_storage.py`

## Cleanup Steps

### Phase 1: Remove from Deployment
1. Remove stack imports from `carpool-bets-stage.ts`
2. Remove stack instantiation
3. Deploy to remove AWS resources

### Phase 2: Remove Code Files
1. Delete backend Python files
2. Delete infrastructure TypeScript files
3. Delete test files

### Phase 3: Clean Documentation
1. Archive old documentation files
2. Update references in remaining docs

## Execution Plan

### Step 1: Infrastructure Removal
```bash
# Remove stacks from deployment
cd infrastructure && make deploy-dev
```

### Step 2: File Cleanup
```bash
# Remove backend files
rm backend/prediction_generator.py
rm backend/prediction_tracker.py
rm backend/recommendation_generator.py
rm backend/recommendation_storage.py
rm backend/bet_recommendations.py

# Remove infrastructure files
rm infrastructure/lib/prediction-generator-stack.ts
rm infrastructure/lib/recommendation-generator-stack.ts

# Remove tests
rm backend/tests/unit/test_prediction_tracker.py
rm backend/tests/unit/test_recommendation_generator.py
rm backend/tests/unit/test_recommendation_storage.py
```

### Step 3: Documentation Cleanup
```bash
# Archive old docs
mkdir docs/archived
mv docs/recommendation-*.md docs/archived/
mv docs/spread-totals-prediction-design.md docs/archived/
```

## Risk Assessment

### Low Risk
- Prediction/recommendation systems are not user-facing
- No production dependencies
- Easy to rollback if needed

### Mitigation
- Keep git history for rollback capability
- Archive documentation rather than delete
- Gradual removal with testing at each step
