"""
AI Agent for natural language model creation and data analysis
Uses AWS Bedrock with Claude 3.5 Sonnet for LLM capabilities
"""
import json
import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import boto3

from user_models import UserModel, validate_model_config


class AIAgent:
    def __init__(self):
        self.bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.table = self.dynamodb.Table(
            os.environ.get("DYNAMODB_TABLE", "carpool-bets-v2-dev")
        )
        # Use foundation model ID directly
        self.model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"

        self.system_prompt = """You are an expert sports betting analyst assistant. You help users:
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

Always be concise, data-driven, and actionable."""

    def execute_tool(
        self, tool_name: str, tool_input: Dict[str, Any], user_id: str = None
    ) -> Dict[str, Any]:
        """Execute a tool and return results with user privacy controls"""
        if tool_name == "create_model":
            return self._create_model(tool_input, user_id)
        elif tool_name == "analyze_predictions":
            return self._analyze_predictions(tool_input, user_id)
        elif tool_name == "query_stats":
            return self._query_stats(tool_input)
        elif tool_name == "explain_prediction":
            return self._explain_prediction(tool_input, user_id)
        elif tool_name == "list_user_models":
            return self._list_user_models(tool_input, user_id)
        elif tool_name == "analyze_bet":
            return self._analyze_bet(tool_input)
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def _create_model(
        self, params: Dict[str, Any], requesting_user_id: str = None
    ) -> Dict[str, Any]:
        """Create a new user model"""
        try:
            user_id = requesting_user_id or params.get("user_id", "ai-agent")
            model_id = str(uuid.uuid4())

            config = {
                "model_name": params["model_name"],
                "sport": params["sport"],
                "bet_types": params["bet_types"],
                "data_sources": params["data_sources"],
                "confidence_threshold": params.get("confidence_threshold", 0.6),
            }

            errors = validate_model_config(config)
            if errors:
                return {"success": False, "errors": errors}

            model = UserModel.create(user_id, model_id, config)
            model.save(self.table)

            return {
                "success": True,
                "model_id": model_id,
                "model_name": config["model_name"],
                "sport": config["sport"],
                "message": f"Model '{config['model_name']}' created successfully",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _analyze_predictions(
        self, params: Dict[str, Any], user_id: str = None
    ) -> Dict[str, Any]:
        """Analyze recent predictions with user privacy"""
        try:
            days_back = params.get("days_back", 7)
            model_id = params.get("model_id")
            cutoff = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

            # If model_id specified, verify user has access
            if model_id and user_id and user_id != "benny":
                model = UserModel.get(user_id, model_id)
                if not model:
                    return {"error": "Model not found or access denied"}

            # Query predictions
            if model_id:
                # Filter by specific model
                response = self.table.query(
                    KeyConditionExpression="PK = :pk AND SK > :cutoff",
                    ExpressionAttributeValues={
                        ":pk": f"MODEL#{model_id}#PREDICTIONS",
                        ":cutoff": cutoff,
                    },
                    Limit=100,
                )
            else:
                # All predictions (Benny can see all, users see their own)
                response = self.table.query(
                    IndexName="GSI1",
                    KeyConditionExpression="GSI1PK = :pk AND GSI1SK > :cutoff",
                    ExpressionAttributeValues={":pk": "PREDICTIONS", ":cutoff": cutoff},
                    Limit=100,
                )

            predictions = response.get("Items", [])

            # Filter by user_id if not Benny
            if user_id and user_id != "benny":
                predictions = [p for p in predictions if p.get("user_id") == user_id]

            total = len(predictions)
            correct = sum(1 for p in predictions if p.get("outcome") == "correct")
            accuracy = (correct / total * 100) if total > 0 else 0

            return {
                "total_predictions": total,
                "correct_predictions": correct,
                "accuracy": round(accuracy, 2),
                "days_analyzed": days_back,
            }
        except Exception as e:
            return {"error": str(e)}

    def _query_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Query historical stats"""
        try:
            query_type = params["query_type"]
            team = params.get("team")
            days_back = params.get("days_back", 30)
            cutoff = (datetime.utcnow() - timedelta(days=days_back)).isoformat()

            if query_type == "team_stats" and team:
                response = self.table.query(
                    KeyConditionExpression="PK = :pk AND SK > :cutoff",
                    ExpressionAttributeValues={
                        ":pk": f"TEAM_STATS#{team}",
                        ":cutoff": cutoff,
                    },
                    Limit=10,
                )
                return {"stats": response.get("Items", [])}

            elif query_type == "game_outcomes" and team:
                response = self.table.query(
                    IndexName="GSI1",
                    KeyConditionExpression="GSI1PK = :pk AND GSI1SK > :cutoff",
                    ExpressionAttributeValues={
                        ":pk": f"TEAM#{team}",
                        ":cutoff": cutoff,
                    },
                    Limit=10,
                )
                return {"outcomes": response.get("Items", [])}

            else:
                return {"error": "Invalid query parameters"}

        except Exception as e:
            return {"error": str(e)}

    def _explain_prediction(
        self, params: Dict[str, Any], user_id: str = None
    ) -> Dict[str, Any]:
        """Explain a specific prediction with privacy check"""
        try:
            prediction_id = params["prediction_id"]

            response = self.table.get_item(
                Key={"PK": f"PREDICTION#{prediction_id}", "SK": "METADATA"}
            )

            if "Item" not in response:
                return {"error": "Prediction not found"}

            prediction = response["Item"]

            # Check user access (Benny can see all)
            if user_id and user_id != "benny":
                if prediction.get("user_id") != user_id:
                    return {"error": "Access denied"}

            return {
                "prediction_id": prediction_id,
                "game": prediction.get("game"),
                "prediction": prediction.get("prediction"),
                "confidence": prediction.get("confidence"),
                "data_sources": prediction.get("data_sources_used", {}),
            }
        except Exception as e:
            return {"error": str(e)}

    def _list_user_models(
        self, params: Dict[str, Any], user_id: str = None
    ) -> Dict[str, Any]:
        """List user models with privacy controls"""
        try:
            target_user_id = params.get("user_id")

            # Benny can see all models with allow_benny_access=True
            if user_id == "benny":
                sport = params.get("sport")  # Optional sport filter
                models = UserModel.list_benny_accessible(sport=sport)
            else:
                # Regular users can only see their own models
                if target_user_id and target_user_id != user_id:
                    return {"error": "Access denied"}
                target_user_id = user_id or target_user_id

                if not target_user_id:
                    return {"error": "user_id required"}

                models = UserModel.list_by_user(target_user_id)

            return {
                "models": [
                    {
                        "model_id": m.model_id,
                        "name": m.name,
                        "sport": m.sport,
                        "bet_types": m.bet_types,
                        "status": m.status,
                        "created_at": m.created_at,
                    }
                    for m in models
                ]
            }
        except Exception as e:
            return {"error": str(e)}

    def retrieve_context(
        self, query: str, user_id: str = None, context_type: str = "auto"
    ) -> str:
        """
        Retrieve relevant context from DynamoDB based on query with privacy controls
        This is a simple RAG implementation without vector embeddings
        """
        try:
            context_parts = []

            # Extract entities from query (simple keyword matching)
            query_lower = query.lower()

            # Check for team mentions
            if any(word in query_lower for word in ["team", "stats", "performance"]):
                team_stats = self._get_recent_team_stats()
                if team_stats:
                    context_parts.append(
                        f"Recent team statistics:\n{json.dumps(team_stats, indent=2)}"
                    )

            # Check for prediction/model mentions
            if any(word in query_lower for word in ["prediction", "model", "accuracy"]):
                recent_predictions = self._get_recent_predictions(user_id)
                if recent_predictions:
                    context_parts.append(
                        f"Recent predictions:\n{json.dumps(recent_predictions, indent=2)}"
                    )

            # Check for game/outcome mentions
            if any(
                word in query_lower for word in ["game", "outcome", "result", "score"]
            ):
                recent_games = self._get_recent_games()
                if recent_games:
                    context_parts.append(
                        f"Recent game outcomes:\n{json.dumps(recent_games, indent=2)}"
                    )

            return "\n\n".join(context_parts) if context_parts else ""

        except Exception as e:
            print(f"Error retrieving context: {e}")
            return ""

    def _get_recent_team_stats(self, limit: int = 5) -> List[Dict]:
        """Get recent team statistics"""
        try:
            cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :pk AND GSI1SK > :cutoff",
                ExpressionAttributeValues={":pk": "TEAM_STATS", ":cutoff": cutoff},
                Limit=limit,
            )
            return response.get("Items", [])
        except Exception:
            return []

    def _get_recent_predictions(
        self, user_id: str = None, limit: int = 10
    ) -> List[Dict]:
        """Get recent predictions with privacy filtering"""
        try:
            cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :pk AND GSI1SK > :cutoff",
                ExpressionAttributeValues={":pk": "PREDICTIONS", ":cutoff": cutoff},
                Limit=limit * 2,  # Get more to filter
            )
            predictions = response.get("Items", [])

            # Filter by user_id if not Benny
            if user_id and user_id != "benny":
                predictions = [p for p in predictions if p.get("user_id") == user_id]

            return predictions[:limit]
        except Exception:
            return []

    def _get_recent_games(self, limit: int = 10) -> List[Dict]:
        """Get recent game outcomes"""
        try:
            cutoff = (datetime.utcnow() - timedelta(days=7)).isoformat()
            response = self.table.query(
                IndexName="GSI1",
                KeyConditionExpression="GSI1PK = :pk AND GSI1SK > :cutoff",
                ExpressionAttributeValues={":pk": "OUTCOMES", ":cutoff": cutoff},
                Limit=limit,
            )
            return response.get("Items", [])
        except Exception:
            return []

    def chat(
        self,
        message: str,
        user_id: str = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        stream: bool = True,
    ):
        """Send a message and get streaming response with RAG context"""
        messages = conversation_history or []

        # Retrieve relevant context using RAG with privacy
        context = self.retrieve_context(message, user_id)

        # Add context to system prompt if available
        system_prompt = self.system_prompt
        if context:
            system_prompt += f"\n\nRelevant context from database:\n{context}"

        messages.append({"role": "user", "content": message})

        request_body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": messages,
            "tools": self._get_tools(),
            "temperature": 0.7,
        }

        if stream:
            return self._stream_response(request_body)
        else:
            return self._invoke_model(request_body)

    def _stream_response(self, request_body: Dict[str, Any]):
        """Stream response from Bedrock"""
        response = self.bedrock.invoke_model_with_response_stream(
            modelId=self.model_id, body=json.dumps(request_body)
        )

        for event in response["body"]:
            chunk = json.loads(event["chunk"]["bytes"])
            yield chunk

    def _invoke_model(self, request_body: Dict[str, Any]) -> Dict[str, Any]:
        """Non-streaming invocation"""
        response = self.bedrock.invoke_model(
            modelId=self.model_id, body=json.dumps(request_body)
        )

        return json.loads(response["body"].read())

    def _analyze_bet(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze a specific bet on-the-spot"""
        try:
            sport = params["sport"]
            bet_type = params["bet_type"]
            team_or_player = params["team_or_player"]
            opponent = params.get("opponent")
            line = params["line"]
            odds = params.get("odds", -110)

            # Calculate implied probability and ROI
            if odds < 0:
                implied_prob = abs(odds) / (abs(odds) + 100)
                roi_multiplier = 100 / abs(odds)
            else:
                implied_prob = 100 / (odds + 100)
                roi_multiplier = odds / 100

            # Query recent performance
            stats_result = self._query_stats(
                {
                    "query_type": "team_stats"
                    if bet_type != "prop"
                    else "player_stats",
                    "team": team_or_player if bet_type != "prop" else None,
                    "player": team_or_player if bet_type == "prop" else None,
                    "opponent": opponent,
                    "days_back": 30,
                }
            )

            # Calculate risk level based on implied probability
            if implied_prob > 0.65:
                risk_level = "conservative"
            elif implied_prob > 0.55:
                risk_level = "moderate"
            else:
                risk_level = "aggressive"

            return {
                "success": True,
                "bet_details": {
                    "sport": sport,
                    "bet_type": bet_type,
                    "team_or_player": team_or_player,
                    "opponent": opponent,
                    "line": line,
                    "odds": odds,
                },
                "analysis": {
                    "implied_probability": round(implied_prob * 100, 1),
                    "roi_multiplier": round(roi_multiplier, 2),
                    "risk_level": risk_level,
                    "recent_stats": stats_result,
                },
                "recommendation": f"This is a {risk_level} risk bet with {round(implied_prob * 100, 1)}% implied probability. ROI multiplier: {round(roi_multiplier, 2)}x",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_tools(self) -> List[Dict[str, Any]]:
        """Define available tools for the agent"""
        return [
            {
                "name": "create_model",
                "description": "Create a new betting model with specified data sources and weights",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "model_name": {
                            "type": "string",
                            "description": "Name for the model",
                        },
                        "sport": {
                            "type": "string",
                            "enum": [
                                "basketball_nba",
                                "americanfootball_nfl",
                                "icehockey_nhl",
                                "baseball_mlb",
                                "soccer_epl",
                            ],
                            "description": "Sport for the model",
                        },
                        "bet_types": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": ["h2h", "spreads", "totals", "props"],
                            },
                            "description": "Types of bets to predict",
                        },
                        "data_sources": {
                            "type": "object",
                            "properties": {
                                "team_stats": {
                                    "type": "object",
                                    "properties": {
                                        "enabled": {"type": "boolean"},
                                        "weight": {"type": "number"},
                                    },
                                },
                                "odds_movement": {
                                    "type": "object",
                                    "properties": {
                                        "enabled": {"type": "boolean"},
                                        "weight": {"type": "number"},
                                    },
                                },
                                "recent_form": {
                                    "type": "object",
                                    "properties": {
                                        "enabled": {"type": "boolean"},
                                        "weight": {"type": "number"},
                                    },
                                },
                                "rest_schedule": {
                                    "type": "object",
                                    "properties": {
                                        "enabled": {"type": "boolean"},
                                        "weight": {"type": "number"},
                                    },
                                },
                                "head_to_head": {
                                    "type": "object",
                                    "properties": {
                                        "enabled": {"type": "boolean"},
                                        "weight": {"type": "number"},
                                    },
                                },
                            },
                        },
                        "confidence_threshold": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "Minimum confidence to make prediction",
                        },
                    },
                    "required": ["model_name", "sport", "bet_types", "data_sources"],
                },
            },
            {
                "name": "analyze_predictions",
                "description": "Analyze recent predictions for a model or sport",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "model_id": {
                            "type": "string",
                            "description": "Model ID to analyze (optional)",
                        },
                        "sport": {
                            "type": "string",
                            "description": "Sport to analyze (optional)",
                        },
                        "days_back": {
                            "type": "integer",
                            "default": 7,
                            "description": "Number of days to look back",
                        },
                    },
                },
            },
            {
                "name": "query_stats",
                "description": "Query historical game outcomes, team stats, or player performance",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "query_type": {
                            "type": "string",
                            "enum": [
                                "team_stats",
                                "player_stats",
                                "game_outcomes",
                                "head_to_head",
                            ],
                            "description": "Type of data to query",
                        },
                        "team": {
                            "type": "string",
                            "description": "Team name (optional)",
                        },
                        "player": {
                            "type": "string",
                            "description": "Player name (optional)",
                        },
                        "opponent": {
                            "type": "string",
                            "description": "Opponent team (optional)",
                        },
                        "days_back": {
                            "type": "integer",
                            "default": 30,
                            "description": "Number of days to look back",
                        },
                    },
                    "required": ["query_type"],
                },
            },
            {
                "name": "explain_prediction",
                "description": "Explain why a specific prediction was made",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "prediction_id": {
                            "type": "string",
                            "description": "Prediction ID to explain",
                        },
                        "include_data_sources": {
                            "type": "boolean",
                            "default": True,
                            "description": "Include data source details",
                        },
                    },
                    "required": ["prediction_id"],
                },
            },
            {
                "name": "list_user_models",
                "description": "List all models for a user. Users can only see their own models.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "User ID to list models for",
                        },
                    },
                    "required": ["user_id"],
                },
            },
            {
                "name": "analyze_bet",
                "description": "Analyze a specific bet idea on-the-spot - calculate risk, ROI potential, key factors. Use when user asks about a bet that isn't in our predictions.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "sport": {
                            "type": "string",
                            "description": "Sport (e.g., basketball_nba, americanfootball_nfl)",
                        },
                        "bet_type": {
                            "type": "string",
                            "enum": ["h2h", "spread", "total", "prop"],
                            "description": "Type of bet",
                        },
                        "team_or_player": {
                            "type": "string",
                            "description": "Team or player name",
                        },
                        "opponent": {
                            "type": "string",
                            "description": "Opponent team (optional)",
                        },
                        "line": {
                            "type": "string",
                            "description": "Betting line (e.g., '-5.5', 'over 220.5', 'over 25.5 points')",
                        },
                        "odds": {
                            "type": "number",
                            "description": "American odds (e.g., -110, +150)",
                        },
                    },
                    "required": ["sport", "bet_type", "team_or_player", "line"],
                },
            },
        ]


def lambda_handler(event, context):
    """Lambda handler for AI agent chat endpoint"""
    try:
        body = json.loads(event.get("body", "{}"))
        message = body.get("message")
        conversation_id = body.get("conversation_id")
        stream = body.get("stream", True)

        # Extract user_id from request context (set by authorizer)
        user_id = None
        if "requestContext" in event and "authorizer" in event["requestContext"]:
            claims = event["requestContext"]["authorizer"].get("claims", {})
            user_id = claims.get("sub") or claims.get("cognito:username")

        if not message:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "message is required"}),
            }

        agent = AIAgent()

        # TODO: Load conversation history from DynamoDB if conversation_id provided
        conversation_history = []

        if stream:
            # For streaming, we'll need to use API Gateway WebSocket or return chunks
            # For now, return non-streaming response
            response = agent._invoke_model(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "system": agent.system_prompt,
                    "messages": conversation_history
                    + [{"role": "user", "content": message}],
                    "tools": agent._get_tools(),
                    "temperature": 0.7,
                }
            )

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "conversation_id": conversation_id or "new",
                        "response": response,
                        "user_id": user_id,
                    }
                ),
            }
        else:
            response = agent._invoke_model(
                {
                    "anthropic_version": "bedrock-2023-05-31",
                    "max_tokens": 4096,
                    "system": agent.system_prompt,
                    "messages": conversation_history
                    + [{"role": "user", "content": message}],
                    "tools": agent._get_tools(),
                    "temperature": 0.7,
                }
            )

            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "conversation_id": conversation_id or "new",
                        "response": response,
                        "user_id": user_id,
                    }
                ),
            }

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # Emit CloudWatch metric
        try:
            import boto3
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.put_metric_data(
                Namespace='SportsAnalytics/AIAgent',
                MetricData=[{
                    'MetricName': 'ChatError',
                    'Value': 1,
                    'Unit': 'Count'
                }]
            )
        except:
            pass
        
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
