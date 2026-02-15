# Session Notes - February 14, 2026

## Work Completed

### 1. Fixed Benny AI Chat Authentication
**Problem**: Benny AI chat returning "Sorry, I encountered an error" for all requests
**Root Cause**: 
- Missing authentication token in API requests
- Missing CORS headers in Lambda responses
- Wrong API Gateway URL (using main API instead of AI Agent API)

**Solution**:
- Added `token` prop to Benny component
- Added Authorization header to chat API requests: `Authorization: Bearer ${token}`
- Added CORS headers to all Lambda responses in `ai_agent_api.py`
- Created separate `REACT_APP_AI_AGENT_API_URL` environment variable
- Passed `user_id` parameter to `agent.chat()` method

**Files Modified**:
- `backend/ai_agent_api.py` - Added CORS headers, fixed user_id parameter
- `frontend/src/components/Benny.tsx` - Added token prop and auth header
- `frontend/src/App.tsx` - Pass token to Benny component
- `frontend/.env` - Added REACT_APP_AI_AGENT_API_URL

### 2. Fixed Free Tier Benny Access
**Problem**: Free tier users had benny_ai=True in subscription stub
**Solution**: Changed to benny_ai=False in `backend/api/user.py`

**Files Modified**:
- `backend/api/user.py`

### 3. Investigated and Fixed Analysis Generator Throttling
**Problem**: Staging environment experiencing intermittent Lambda throttling on analysis generators
**Investigation Findings**:
- 100 EventBridge rules firing every 4 hours (5 sports × 10 models × 2 bet types)
- Rules staggered by only 1 minute
- Individual Lambda runs take 1-30 seconds
- When spread over 100 minutes, invocations overlap causing throttling
- Max concurrent executions: 10 (well below 1000 account limit)
- Throttling is intermittent burst limit issue, not sustained concurrency

**Root Cause**: 
- SYSTEM_MODELS constant has 10 models (consensus, value, momentum, contrarian, hot_cold, rest_schedule, matchup, injury_aware, news, ensemble)
- Each model × 2 bet types × 5 sports = 100 invocations per 4-hour cycle
- 1-minute stagger insufficient when runs take >1 minute

**Solution**: Increased stagger from 1 to 2 minutes
- Spreads 100 invocations over 200 minutes instead of 100
- Reduces peak concurrent executions
- Prevents burst limit throttling

**Files Modified**:
- `infrastructure/lib/analysis-generator-schedule-stack.ts`

**Why Dev Doesn't See This**: Random/intermittent issue - both environments identical, staging just unlucky with timing

## Deployments Needed

1. **AI Agent Lambda** (dev and staging)
   ```bash
   cd infrastructure
   make deploy-ai-agent ENV=dev
   make deploy-ai-agent ENV=beta
   ```

2. **Analysis Generator Schedule Stack** (staging only for now)
   ```bash
   cd infrastructure
   cdk deploy Beta-AnalysisSchedule --profile sports-betting-staging
   ```

3. **Frontend Dev Server** - Restart to pick up new REACT_APP_AI_AGENT_API_URL environment variable

## Next Steps

### Immediate (from TODO list)
1. Create beta tester user accounts in Cognito
2. Fix duplicate analysis items for user models in game analysis
3. Add user models to model leaderboard and comparison
4. Fix intermittent user model loading failures (403 errors)

### Follow-up
- Monitor staging throttling alarms after schedule stack deployment
- If throttling persists, consider:
  - Increasing stagger to 3 minutes
  - Adding reserved concurrency to analysis generators
  - Investigating DynamoDB throttling

## Git Commits
- `fix: disable Benny AI for free tier users`
- `fix: add authentication to Benny AI chat`
- `fix: add CORS headers and separate AI Agent API URL`
- `fix: pass user_id to AI agent chat method`
- `fix: increase analysis generator stagger from 1 to 2 minutes`
