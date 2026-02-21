# Sports Betting Analytics - Development Workflow

## 🎯 Daily Development Process

### AWS Profile Configuration
- **Dev Account Profile**: `sports-betting-dev`
- All dev environment operations use this profile automatically via Makefile
- For manual AWS CLI commands, always specify: `AWS_PROFILE=sports-betting-dev`

### Step-by-Step Workflow
1. **Identify Task**: Review PROJECT_STATUS.md and select next task
2. **Update Status**: Mark task as "In Progress" in PROJECT_STATUS.md
3. **Implement**: Write code for the task
4. **Test**: Create unit tests and integration tests as needed
5. **Build Check**: Run `make workflow-check` to verify everything works
6. **Fix Issues**: Address any linting, test, or build failures
7. **Deploy Dev** (if CDK changes): Deploy to dev stack and verify
8. **Update Docs**: Mark task complete in PROJECT_STATUS.md
9. **Log Learnings**: Add insights to TROUBLESHOOTING_AND_LESSONS.md
10. **Commit & Push**: Commit changes and push to trigger pipeline
11. **Monitor Pipeline**: Check deployment status asynchronously

### Quality Gates
- **All tests pass** before committing
- **High test coverage** maintained
- **Code automatically linted** and fixed
- **Build succeeds** on all components
- **Dev deployment works** (for infrastructure changes)

## 📝 Task Management

### PROJECT_STATUS.md Format
Tasks should be tracked with these statuses:
- **⏳ Not Started** - Task identified but not begun
- **🚧 In Progress** - Currently working on this task
- **✅ Complete** - Task finished and tested
- **🔄 Testing** - Implementation done, testing in progress
- **🚀 Deploying** - Deployed to dev, verifying functionality

### Status Update Commands
```bash
# Quick status check
make status-check

# Update task status (interactive)
make update-task-status
```

## 🧪 Testing & Quality Assurance

### Automated Quality Checks
```bash
# Run full workflow check (linting, tests, build)
make workflow-check

# Individual components
make lint-fix      # Auto-fix linting issues
make test         # Run all tests
make build        # Build all components
```

### Test Coverage Requirements
- **Unit tests** for all new code
- **Integration tests** for API endpoints and data flows
- **High coverage** maintained (aim for >90% line and branch coverage)
- **All tests pass** before any commit
- **Coverage commands**:
  - `make test-coverage` - Full backend coverage report
  - `make test-coverage-module MODULE=<module_name>` - Specific module coverage
  - Both commands show line and branch coverage metrics

### Writing Unit Tests - Critical Rules
**ALWAYS read the implementation code FIRST before writing tests:**

1. **Read the actual implementation** to understand:
   - Method signatures and parameters
   - Dependencies (e.g., `self.table` from BaseAPIHandler)
   - Required vs optional parameters
   - Expected return values and data structures
   - Error handling behavior

2. **Check existing test patterns** in the codebase:
   - How dependencies are mocked
   - Import patterns and environment setup
   - Assertion styles used

3. **Write tests that match reality**:
   - Use actual method signatures from the code
   - Mock all dependencies the code actually uses
   - Test with realistic data structures
   - Verify actual return values, not assumptions

4. **Common pitfalls to avoid**:
   - ❌ Guessing method signatures without reading code
   - ❌ Mocking wrong import paths
   - ❌ Testing with incomplete mock data
   - ❌ Asserting on wrong response keys
   - ✅ Read implementation → Understand dependencies → Write matching tests

**Example workflow:**
```bash
# 1. Read the implementation
cat backend/api/games.py | grep "def get_games"

# 2. Check what it imports/uses
cat backend/api/games.py | grep "import\|from"

# 3. Look at similar existing tests
cat backend/tests/unit/test_api_handler.py

# 4. Write test matching actual implementation
```

### Code Quality Standards
- **Automatic linting** with auto-fix enabled
- **Python**: black + flake8 + isort
- **TypeScript**: ESLint + Prettier
- **Consistent formatting** across all files

## 🚀 Deployment & Pipeline Monitoring

### Development Environment
```bash
# Deploy to dev (manual only) - uses sports-betting-dev profile
make deploy-dev

# Verify dev deployment
make verify-dev

# Clear DynamoDB table (use ops directory)
cd ../ops && AWS_PROFILE=sports-betting-dev python3 clear_table.py

### Lambda Testing Workflow
Complete testing sequence for Lambda functions:

```bash
# 1. Clear DynamoDB table
cd ../ops && AWS_PROFILE=sports-betting-dev python3 clear_table.py

# 2. Deploy all stacks to dev
cd ../infrastructure && make deploy-dev

# 3. Test Lambda functions in order:

# Step 3a: Test Odds Collector
AWS_PROFILE=sports-betting-dev aws lambda invoke --function-name Dev-OddsCollector-OddsCollectorFunction6A9C6277-RXibwu37zOli /tmp/response.json
cat /tmp/response.json
# Verify: Check DynamoDB for game/prop data

# Step 3b: Test Prediction Generator  
echo '{"sport":"basketball_nba","model":"consensus","bet_type":"props","limit":5}' | base64 | tr -d '\n' > /tmp/payload.b64
AWS_PROFILE=sports-betting-dev aws lambda invoke --function-name Dev-PredictionGenerator-PredictionGeneratorFunctio-nUbb1Nq1bDK4 --payload file:///tmp/payload.b64 /tmp/response.json
cat /tmp/response.json
# Verify: Check DynamoDB for prediction data

# Step 3c: Test Recommendation Generator
echo '{"sport":"basketball_nba","bookmaker":"fanduel","model":"consensus","risk_level":"conservative","bet_type":"props"}' | base64 | tr -d '\n' > /tmp/payload.b64
AWS_PROFILE=sports-betting-dev aws lambda invoke --function-name Dev-RecommendationGenerat-RecommendationGeneratorF-94DTeKirnv2I --payload file:///tmp/payload.b64 /tmp/response.json
cat /tmp/response.json
# Verify: Check response for recommendations

# 4. Check logs for any errors (replace FUNCTION_NAME and STREAM_NAME)
AWS_PROFILE=sports-betting-dev aws logs describe-log-streams --log-group-name /aws/lambda/FUNCTION_NAME --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text
AWS_PROFILE=sports-betting-dev aws logs get-log-events --log-group-name /aws/lambda/FUNCTION_NAME --log-stream-name STREAM_NAME

# 5. If errors found: Fix code, redeploy, repeat testing
```

**Testing Rules:**
- Always test in order: Odds Collector → Prediction Generator → Recommendation Generator
- Verify DynamoDB state and Lambda logs after each step
- Fix any errors immediately before proceeding to next Lambda
- Clear table and redeploy if major changes are made

# Check dev resources
AWS_PROFILE=sports-betting-dev aws cloudformation list-stacks --stack-status-filter CREATE_COMPLETE UPDATE_COMPLETE --query 'StackSummaries[].StackName' --output table

# View Lambda logs
AWS_PROFILE=sports-betting-dev aws logs describe-log-streams --log-group-name /aws/lambda/FUNCTION_NAME --order-by LastEventTime --descending --max-items 1 --query 'logStreams[0].logStreamName' --output text
AWS_PROFILE=sports-betting-dev aws logs get-log-events --log-group-name /aws/lambda/FUNCTION_NAME --log-stream-name STREAM_NAME
```

### Pipeline Monitoring
```bash
# Check pipeline status
make check-pipeline

# Get pipeline logs (if failed)
make pipeline-logs

# Monitor deployment progress
make monitor-deployment
```

### Environment Strategy
- **Dev**: Manual deployment for testing with real AWS resources
- **Staging/Prod**: Automatic deployment through pipeline only
- **Pipeline**: Triggers on push to main branch

## 🔄 Example Development Session

1. **Start**: Review current status and recent lessons
2. **Plan**: "Add NBA API integration for game data"
3. **Test**: Write tests for API client and data parsing
4. **Implement**: FastAPI endpoints and data models
5. **Verify**: Deploy to Dev, test API endpoints
6. **Document**: Update status with completed work
7. **Capture**: Log decision rationale and any challenges
8. **Commit**: "feat: Add NBA API integration for game data"
9. **Push**: Immediate push to GitHub
10. **Update**: Status document and lessons learned

### Session End Checklist
- [ ] All tests passing
- [ ] Code committed and pushed
- [ ] Status document updated
- [ ] Lessons learned captured
- [ ] Next step clearly defined
- [ ] Architecture decisions documented

## 🏗️ Project-Specific Patterns

### Python Development
- Use **virtual environments** for dependency isolation
- Follow **PEP 8** style guidelines
- Use **type hints** for better code documentation
- **pytest** for testing framework

### FastAPI Patterns
- **Dependency injection** for database connections
- **Pydantic models** for request/response validation
- **Async/await** for I/O operations
- **Background tasks** for long-running operations

### ML Pipeline
- **Data validation** at ingestion points
- **Model versioning** for reproducibility
- **Feature engineering** documentation
- **Performance monitoring** for model drift

### Sports Data Integration
- **Rate limiting** for API calls
- **Data caching** to reduce API usage
- **Error handling** for API failures
- **Data quality checks** for incoming data

---

*Created: 2025-12-28*  
*Status: Development Workflow Defined*  
*Next: Apply this workflow to current development phase*
