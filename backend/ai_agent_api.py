"""
AI Agent API Lambda handler
Provides chat endpoint for natural language model creation and data analysis
"""
import json
from typing import Any, Dict

from ai_agent import AIAgent


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Handle AI Agent API requests"""
    cors_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST",
    }

    try:
        path = event.get("path", "")
        method = event.get("httpMethod", "")

        if path == "/ai-agent/chat" and method == "POST":
            return handle_chat(event, cors_headers)
        else:
            return {
                "statusCode": 404,
                "body": json.dumps({"error": "Not found"}),
                "headers": cors_headers,
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
                Namespace='SportsAnalytics/AIAgentAPI',
                MetricData=[{
                    'MetricName': 'APIError',
                    'Value': 1,
                    'Unit': 'Count'
                }]
            )
        except:
            pass
        
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": cors_headers,
        }


def handle_chat(event: Dict[str, Any], cors_headers: Dict[str, str]) -> Dict[str, Any]:
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
                "headers": cors_headers,
            }

        if not user_id:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "user_id is required"}),
                "headers": cors_headers,
            }

        agent = AIAgent()

        # Non-streaming response for Lambda
        response = agent.chat(
            message=message,
            user_id=user_id,
            conversation_history=conversation_history,
            stream=False,
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"response": response, "conversation_history": conversation_history}
            ),
            "headers": cors_headers,
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": cors_headers,
        }
