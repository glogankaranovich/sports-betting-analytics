# AI Agent Architecture

## Overview
An AI-powered assistant that helps users create custom betting models, analyze data, and optimize predictions using natural language.

## Core Capabilities

### 1. Model Creation Assistant
**User Input:** Natural language description of betting strategy
**Example:** "I want to bet on NBA teams with 3+ days rest playing against teams on back-to-backs"

**Agent Actions:**
- Parse user intent and extract key features
- Generate Python model code using BaseAnalysisModel template
- Suggest additional features (injuries, home/away, etc.)
- Test model on historical data
- Deploy to user's model collection

### 2. Data Analysis Agent
**User Input:** Questions about performance or patterns
**Examples:**
- "Why is my momentum model underperforming on props?"
- "Which models work best for NBA home underdogs?"
- "Show me games where consensus and value models disagreed"

**Agent Actions:**
- Query DynamoDB for relevant historical data
- Analyze patterns using statistical methods
- Generate visualizations and insights
- Suggest model improvements

### 3. Prediction Explainer
**User Input:** Request to explain a specific prediction
**Example:** "Why did the carpool model pick Lakers -5.5?"

**Agent Actions:**
- Retrieve prediction details and contributing models
- Show weight distribution and confidence factors
- Compare to other models' predictions
- Highlight key data points (injuries, rest, momentum)

### 4. Model Optimizer
**User Input:** Request to improve model performance
**Example:** "Optimize my rest model for better accuracy"

**Agent Actions:**
- Analyze model's historical performance
- Identify weak spots (bet types, situations, teams)
- Suggest parameter adjustments
- A/B test changes on historical data
- Deploy optimized version

## Technical Architecture

### Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend UI                           │
│  - Chat interface                                            │
│  - Model builder wizard                                      │
│  - Analysis dashboard                                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway + Lambda                      │
│  - Route requests to appropriate agent                       │
│  - Handle authentication                                     │
│  - Stream responses                                          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      AI Agent Core                           │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  LLM Interface (Claude/GPT-4)                        │  │
│  │  - Natural language understanding                    │  │
│  │  - Code generation                                   │  │
│  │  - Reasoning and explanation                         │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  RAG System (Retrieval Augmented Generation)        │  │
│  │  - Vector DB (Pinecone/Weaviate)                    │  │
│  │  - Embeddings of historical predictions             │  │
│  │  - Model documentation and examples                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Tool Integration Layer                              │  │
│  │  - DynamoDB queries                                  │  │
│  │  - Model execution                                   │  │
│  │  - Code validation                                   │  │
│  │  - Backtesting engine                                │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                                │
│  - DynamoDB (predictions, outcomes, models)                  │
│  - S3 (model code, training data)                            │
│  - Vector DB (embeddings for RAG)                            │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Details

#### 1. LLM Integration
**Provider:** AWS Bedrock (Claude 3) or OpenAI API
**Prompt Engineering:**
- System prompt with betting domain knowledge
- Few-shot examples of model creation
- Structured output for code generation

**Example Prompt:**
```
You are an expert sports betting analyst and Python developer. 
You help users create custom betting models using our BaseAnalysisModel framework.

Available data:
- Game odds (spreads, totals, moneylines)
- Team statistics (last 10 games)
- Player injuries
- Rest days and schedule
- Historical head-to-head

When creating a model:
1. Inherit from BaseAnalysisModel
2. Implement analyze_game_odds() and analyze_prop_odds()
3. Return AnalysisResult with prediction, confidence, reasoning
4. Use helper methods: american_to_decimal(), calculate_implied_probability()

User request: {user_input}
```

#### 2. RAG System
**Vector Database:** Pinecone or AWS OpenSearch
**Embeddings:** 
- All historical predictions with outcomes
- Model documentation and code examples
- Successful betting patterns

**Query Flow:**
1. User asks question
2. Embed question using same model
3. Retrieve top-k relevant documents
4. Pass to LLM as context
5. Generate response

#### 3. Tool Functions
Agent can call these functions:

```python
tools = [
    {
        "name": "query_predictions",
        "description": "Query historical predictions from DynamoDB",
        "parameters": {
            "model": "string",
            "sport": "string", 
            "date_range": "string",
            "outcome": "correct|incorrect|all"
        }
    },
    {
        "name": "backtest_model",
        "description": "Test model on historical data",
        "parameters": {
            "model_code": "string",
            "start_date": "string",
            "end_date": "string"
        }
    },
    {
        "name": "deploy_model",
        "description": "Deploy model to production",
        "parameters": {
            "model_name": "string",
            "model_code": "string",
            "description": "string"
        }
    },
    {
        "name": "analyze_performance",
        "description": "Analyze model performance metrics",
        "parameters": {
            "model": "string",
            "metric": "accuracy|brier|roi",
            "breakdown": "sport|bet_type|confidence"
        }
    }
]
```

#### 4. Code Generation & Validation
**Safety:**
- Sandbox execution environment (AWS Lambda)
- Code review before deployment
- Rate limiting on model creation
- Validation against BaseAnalysisModel interface

**Template:**
```python
class UserCustomModel(BaseAnalysisModel):
    """Generated by AI Agent"""
    
    def analyze_game_odds(self, game_id, odds_items, game_info):
        # AI-generated logic here
        pass
    
    def analyze_prop_odds(self, prop_item):
        # AI-generated logic here
        pass
```

## User Flows

### Flow 1: Create Custom Model
1. User: "Create a model that bets on NBA teams with 3+ days rest"
2. Agent: Generates model code, explains logic
3. User: Reviews and approves
4. Agent: Backtests on last 30 days
5. Agent: Shows results (accuracy, sample predictions)
6. User: Deploys or requests modifications

### Flow 2: Analyze Performance
1. User: "Why is momentum model bad at props?"
2. Agent: Queries prop predictions, calculates metrics
3. Agent: Identifies patterns (e.g., "Struggles with player props, good at team totals")
4. Agent: Suggests improvements (e.g., "Add player injury data")
5. User: Asks agent to implement suggestion

### Flow 3: Explain Prediction
1. User clicks "Explain" on a prediction
2. Agent retrieves prediction details
3. Agent: "Carpool picked Lakers -5.5 because:
   - Momentum model (25% weight): Lakers won last 5
   - Rest model (20% weight): Lakers had 2 days rest, Celtics on back-to-back
   - Value model (18% weight): Line moved from -4.5 to -5.5, sharp action"
4. User understands reasoning

## Infrastructure Requirements

### AWS Services
- **Bedrock/SageMaker:** LLM hosting
- **Lambda:** Agent execution, tool functions
- **API Gateway:** WebSocket for streaming responses
- **DynamoDB:** Conversation history, user models
- **S3:** Model code storage, training data
- **OpenSearch/Pinecone:** Vector database for RAG
- **Step Functions:** Orchestrate complex workflows (backtest → analyze → deploy)

### Cost Estimates (per 1000 users)
- LLM API calls: $500-1000/month (assuming 10 queries/user/month)
- Vector DB: $100-200/month
- Lambda execution: $50-100/month
- Storage: $20-50/month
**Total: ~$700-1400/month**

## Monetization
- **Free Tier:** 10 agent queries/month, basic model creation
- **Pro Tier ($29/mo):** Unlimited queries, advanced analysis, model optimization
- **Enterprise ($99/mo):** Custom models, priority support, API access

## Security & Privacy
- User models are private by default
- Option to share models in marketplace
- No PII in training data
- Rate limiting to prevent abuse
- Code sandboxing for safety

## Future Enhancements
- Voice interface for mobile
- Automated model tournaments (agent vs agent)
- Social features (share strategies, follow top agents)
- Integration with live betting APIs
- Real-time prediction explanations during games

## Implementation Phases

### Phase 1: MVP (4-6 weeks)
- Basic chat interface
- Simple model creation (template-based)
- Query historical data
- Explain predictions

### Phase 2: Advanced Features (6-8 weeks)
- RAG system with vector DB
- Code generation and validation
- Backtesting engine
- Model optimization

### Phase 3: Production (4-6 weeks)
- Scaling and performance
- Monitoring and analytics
- User feedback loop
- Marketplace integration

**Total Timeline: 14-20 weeks**
