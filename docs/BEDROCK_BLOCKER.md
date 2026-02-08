# Phase 2.2: Benny AI Agent - Deployment Blocker

## Status: Infrastructure Complete, Pending Bedrock Access

### What's Built ✅
- AI Agent backend with Claude 3.5 Sonnet integration
- RAG system with DynamoDB context retrieval
- 4 tools: create_model, analyze_predictions, query_stats, explain_prediction
- API endpoint deployed: `https://ddzbfblwr0.execute-api.us-east-1.amazonaws.com/prod/ai-agent/chat`
- Benny floating chat widget in frontend
- 196 unit tests passing
- 6 integration tests ready

### Blocker: AWS Bedrock Model Access

**Issue**: AWS Bedrock requires a use case form with a valid company website/domain to enable Claude models.

**Error**: `ResourceNotFoundException: Model use case details have not been submitted for this account`

**Required for form**:
- Valid company website URL
- Company information
- Use case description

### Options

1. **Get a domain** (Recommended)
   - Register domain (e.g., carpoolbets.com)
   - Create simple landing page
   - Submit Bedrock use case form
   - Wait ~15 min for approval
   - Benny goes live!

2. **Use different LLM** (Alternative)
   - Switch to OpenAI API (requires API key, ~$0.06/conversation)
   - Switch to Amazon Titan (lower quality, no tool calling)
   - Switch to open source model (requires hosting)

3. **Deploy without AI Agent** (Temporary)
   - Deploy frontend without Benny
   - Add Benny later when Bedrock access approved
   - All other features work

### Recommendation

**Get a domain** - It's the cleanest solution:
- Professional appearance
- Enables Bedrock access
- Can use for production deployment
- Cost: ~$12/year for domain

Once domain is set up:
1. Submit Bedrock use case form
2. Wait for approval (~15 min)
3. Run integration tests to verify
4. Deploy frontend with Benny
5. Phase 2.2 complete!

### Current State

All code is ready and tested. The only missing piece is AWS Bedrock model access, which requires a valid domain for the use case form.

**Infrastructure deployed**:
- ✅ Lambda function: `ai-agent-dev`
- ✅ API Gateway endpoint
- ✅ DynamoDB permissions
- ✅ Bedrock permissions (model access pending)
- ✅ Frontend code ready

**Next action**: Acquire domain → Submit Bedrock form → Enable Benny
