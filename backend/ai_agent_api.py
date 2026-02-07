"""
AI Agent API Lambda handler
Provides chat endpoint for natural language model creation and data analysis
"""
import json
from typing import Any, Dict

from ai_agent import AIAgent


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle AI Agent API requests"""
    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "")

        if path == "/ai-agent/chat" and method == "POST":
            return handle_chat(event)
        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Not found"}),
                "headers": {"Content-Type": "application/json"},
            }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }


def handle_chat(event: Dict[str, Any]) -> Dict[str, Any]:
    """Handle chat requests"""
    try:
        body = json.loads(event.get("body", "{}"))
        message = body.get("message")
        conversation_history = body.get("conversation_history", [])
        user_id = body.get("user_id")

        if not message:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "message is required"}),
                "headers": {"Content-Type": "application/json"},
            }

        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "user_id is required"}),
                "headers": {"Content-Type": "application/json"},
            }

        agent = AIAgent()

        # Non-streaming response for Lambda
        response = agent.chat(
            message=message, conversation_history=conversation_history, stream=False
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"response": response, "conversation_history": conversation_history}
            ),
            "headers": {"Content-Type": "application/json"},
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"},
        }
