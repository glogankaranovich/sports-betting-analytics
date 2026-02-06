import json
from datetime import datetime
from typing import Any, Dict, Optional

import boto3


class ComplianceLogger:
    def __init__(self):
        self.dynamodb = boto3.resource("dynamodb")
        self.table = self.dynamodb.Table("sports-betting-compliance-staging")

    def log_user_action(
        self, session_id: str, action: str, user_data: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Log user compliance actions to DynamoDB"""
        try:
            item = {
                "PK": f"SESSION#{session_id}",
                "SK": f"ACTION#{datetime.utcnow().isoformat()}#{action}",
                "action": action,
                "timestamp": datetime.utcnow().isoformat(),
                "session_id": session_id,
                "ttl": int(
                    (datetime.utcnow().timestamp() + (365 * 24 * 3600))
                ),  # 1 year retention
            }

            if user_data:
                item["user_data"] = user_data

            self.table.put_item(Item=item)
            return True

        except Exception as e:
            print(f"Failed to log compliance action: {e}")
            return False

    def log_age_verification(
        self, session_id: str, verified: bool, age: Optional[int] = None
    ) -> bool:
        """Log age verification attempts"""
        return self.log_user_action(
            session_id=session_id,
            action="age_verification",
            user_data={
                "verified": verified,
                "age": age,
                "user_agent": None,  # Will be populated from request headers
            },
        )

    def log_terms_acceptance(
        self,
        session_id: str,
        terms_accepted: bool,
        privacy_accepted: bool,
        risks_accepted: bool,
    ) -> bool:
        """Log terms and conditions acceptance"""
        return self.log_user_action(
            session_id=session_id,
            action="terms_acceptance",
            user_data={
                "terms_accepted": terms_accepted,
                "privacy_accepted": privacy_accepted,
                "risks_accepted": risks_accepted,
            },
        )

    def log_bet_insight_view(
        self, session_id: str, insight_id: str, confidence_score: float
    ) -> bool:
        """Log when user views betting insights"""
        return self.log_user_action(
            session_id=session_id,
            action="insight_viewed",
            user_data={
                "insight_id": insight_id,
                "confidence_score": confidence_score,
            },
        )

    def log_responsible_gambling_access(
        self, session_id: str, resource_type: str
    ) -> bool:
        """Log access to responsible gambling resources"""
        return self.log_user_action(
            session_id=session_id,
            action="responsible_gambling_access",
            user_data={
                "resource_type": resource_type  # 'modal', 'footer_link', 'helpline'
            },
        )

    def get_user_compliance_history(self, session_id: str) -> list:
        """Retrieve compliance history for a session"""
        try:
            response = self.table.query(
                KeyConditionExpression="PK = :pk",
                ExpressionAttributeValues={":pk": f"SESSION#{session_id}"},
                ScanIndexForward=False,  # Most recent first
            )
            return response.get("Items", [])
        except Exception as e:
            print(f"Failed to retrieve compliance history: {e}")
            return []


# Lambda handler for compliance logging
def lambda_handler(event, context):
    """AWS Lambda handler for compliance logging API"""

    compliance_logger = ComplianceLogger()

    try:
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        session_id = body.get("sessionId")
        action = body.get("action")
        data = body.get("data", {})

        if not session_id or not action:
            return {
                "statusCode": 400,
                "body": json.dumps({"error": "Missing required fields"}),
            }

        # Add request metadata
        headers = event.get("headers", {})
        data["user_agent"] = headers.get("User-Agent")
        data["ip_address"] = headers.get("X-Forwarded-For", "unknown")

        # Log the action
        success = compliance_logger.log_user_action(session_id, action, data)

        if success:
            return {
                "statusCode": 200,
                "headers": {
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Headers": "Content-Type",
                    "Access-Control-Allow-Methods": "POST",
                },
                "body": json.dumps({"success": True}),
            }
        else:
            return {
                "statusCode": 500,
                "body": json.dumps({"error": "Failed to log action"}),
            }

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
