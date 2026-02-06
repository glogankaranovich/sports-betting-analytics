# AI Agent Architecture Design

## Overview
Natural language interface for building custom betting models, analyzing predictions, and querying historical data.

## Core Components

### 1. LLM Integration
**Provider:** AWS Bedrock (Claude 3.5 Sonnet)
- Native AWS integration, no API keys needed
- Streaming support for real-time responses
- Tool calling (function calling) built-in
- Cost-effective for production use

**Alternative:** OpenAI GPT-4 (fallback)
- Better for development/testing
- Requires API key management

### 2. Tool Calling Framework
**Available Tools:**
```python
tools = [
    {
        "name": "create_model",
        "description": "Create a new betting model with specified data sources and weights",
        "parameters": {
            "model_name": "string",
            "sport": "enum[basketball_nba, americanfootball_nfl, ...]",
            "bet_types": "array[h2h, spreads, totals, props]",
            "data_sources": {
                "team_stats": {"enabled": bool, "weight": float},
                "odds_movement": {"enabled": bool, "weight": float},
                "recent_form": {"enabled": bool, "weight": float},
                "rest_schedule": {"enabled": bool, "weight": float},
                "head_to_head": {"enabled": bool, "weight": float},
                "player_stats": {"enabled": bool, "weight": float},
                "player_injury": {"enabled": bool, "weight": float}
            },
            "confidence_threshold": float
        }
    },
    {
        "name": "analyze_predictions",
        "description": "Analyze recent predictions for a model or sport",
        "parameters": {
            "model_id": "string (optional)",
            "sport": "string (optional)",
            "days_back": "integer (default: 7)"
        }
    },
    {
        "name": "query_stats",
        "description": "Query historical game outcomes, team stats, or player performance",
        "parameters": {
            "query_type": "enum[team_stats, player_stats, game_outcomes, head_to_head]",
            "team": "string (optional)",
            "player": "string (optional)",
            "opponent": "string (optional)",
            "days_back": "integer (default: 30)"
        }
    },
    {
        "name": "explain_prediction",
        "description": "Explain why a specific prediction was made",
        "parameters": {
            "prediction_id": "string",
            "include_data_sources": bool
        }
    }
]
```

### 3. RAG System (Simplified - No Vector Store Initially)
**Phase 1 (MVP):** Direct DynamoDB queries
- Query recent games, outcomes, stats directly
- No embeddings or vector search needed
- Fast, simple, cost-effective

**Phase 2 (Future):** Vector store for semantic search
- Embed historical game narratives, injury reports
- Use OpenSearch Serverless or Pinecone
- Enable questions like "games where underdog won after rest advantage"

### 4. Conversation State Management
**Storage:** DynamoDB
```python
{
    "PK": "CONVERSATION#{user_id}#{conversation_id}",
    "SK": "MESSAGE#{timestamp}",
    "role": "user|assistant|system",
    "content": "message text",
    "tool_calls": [...],  # if assistant called tools
    "tool_results": [...],  # results from tool execution
    "created_at": "ISO timestamp"
}
```

**Session Management:**
- Keep last 10 messages in context
- Summarize older messages to save tokens
- Store full history in DynamoDB for retrieval

### 5. Prompt Engineering
**System Prompt:**
```
You are an expert sports betting analyst assistant. You help users:
1. Build custom betting models by analyzing their preferences
2. Analyze prediction performance and identify patterns
3. Query historical data to inform betting decisions
4. Explain predictions in clear, actionable terms

When creating models:
- Ask clarifying questions about user's betting style (conservative/aggressive)
- Recommend data sources based on sport and bet type
- Suggest reasonable weights based on historical performance

When analyzing data:
- Provide specific insights with numbers
- Highlight trends and anomalies
- Recommend adjustments to improve performance

Always be concise, data-driven, and actionable.
```

## API Design

### POST /ai-agent/chat
```json
{
  "conversation_id": "uuid (optional, creates new if not provided)",
  "message": "Create a conservative NBA model focusing on team stats",
  "stream": true
}
```

**Response (streaming):**
```
data: {"type": "message", "content": "I'll help you create..."}
data: {"type": "tool_call", "tool": "create_model", "args": {...}}
data: {"type": "tool_result", "result": {...}}
data: {"type": "message", "content": "Model created successfully..."}
data: {"type": "done"}
```

### GET /ai-agent/conversations
```json
{
  "conversations": [
    {
      "conversation_id": "uuid",
      "created_at": "ISO timestamp",
      "last_message": "Create a conservative NBA model...",
      "message_count": 5
    }
  ]
}
```

### GET /ai-agent/conversations/{conversation_id}
```json
{
  "conversation_id": "uuid",
  "messages": [
    {
      "role": "user",
      "content": "Create a conservative NBA model",
      "timestamp": "ISO"
    },
    {
      "role": "assistant",
      "content": "I'll help you create...",
      "tool_calls": [...],
      "timestamp": "ISO"
    }
  ]
}
```

## Implementation Plan

### Phase 1: MVP (Current Sprint)
1. ✅ Design architecture
2. Implement Bedrock integration with Claude 3.5 Sonnet
3. Create tool calling framework (4 tools)
4. Build API endpoints (chat, conversations)
5. Simple UI: chat interface with streaming
6. Deploy and test

### Phase 2: Enhanced (Future)
1. Add vector store for semantic search
2. Add more tools (update_model, delete_model, compare_models)
3. Add conversation summarization
4. Add data visualization in chat responses
5. Add voice input/output

## Technology Stack
- **LLM:** AWS Bedrock (Claude 3.5 Sonnet)
- **Backend:** Python Lambda (ai_agent.py)
- **Storage:** DynamoDB (conversations, messages)
- **API:** API Gateway (REST + WebSocket for streaming)
- **Frontend:** React component (ChatInterface.tsx)

## Cost Estimates
- Claude 3.5 Sonnet: $3 per 1M input tokens, $15 per 1M output tokens
- Average conversation: ~5K tokens input, ~2K tokens output
- Cost per conversation: ~$0.045
- 1000 conversations/month: ~$45/month

## Security Considerations
- Authenticate all API calls with Cognito
- Rate limit: 10 requests/minute per user
- Sanitize user inputs before tool execution
- No PII in conversation logs
- Encrypt conversation data at rest

## Success Metrics
- Average conversation length: 3-5 messages
- Model creation success rate: >80%
- User satisfaction: >4/5 stars
- Response time: <2 seconds for first token
- Tool execution accuracy: >95%

---
**Status:** Design Complete
**Next:** Implement LLM integration layer
