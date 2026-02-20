"""
Miscellaneous API handler (health, compliance, benny dashboard)
"""

import os
from typing import Any, Dict

from api.utils import BaseAPIHandler, table_name


class MiscHandler(BaseAPIHandler):
    """Handler for miscellaneous endpoints"""

    def route_request(
        self,
        http_method: str,
        path: str,
        query_params: Dict[str, str],
        path_params: Dict[str, str],
        body: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Route miscellaneous requests"""
        if path == "/health":
            return self.get_health()
        elif path == "/compliance/log" and http_method == "POST":
            return self.log_compliance(body)
        elif path == "/benny/dashboard" and http_method == "GET":
            return self.get_benny_dashboard()
        else:
            return self.error_response("Endpoint not found", 404)

    def get_health(self) -> Dict[str, Any]:
        """Health check endpoint"""
        return self.success_response(
            {
                "status": "healthy",
                "table": table_name,
                "environment": os.getenv("ENVIRONMENT", "unknown"),
            }
        )

    def log_compliance(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle compliance logging requests"""
        try:
            from compliance_logger import ComplianceLogger

            compliance_logger = ComplianceLogger()
            session_id = body.get("sessionId")
            action = body.get("action")
            data = body.get("data", {})

            if not session_id or not action:
                return self.error_response("Missing required fields: sessionId and action")

            success = compliance_logger.log_user_action(session_id, action, data)

            if success:
                return self.success_response({"success": True})
            else:
                return self.error_response("Failed to log action", 500)

        except Exception as e:
            print(f"Error logging compliance action: {str(e)}")
            return self.error_response(str(e), 500)

    def get_benny_dashboard(self) -> Dict[str, Any]:
        """Get Benny's trading dashboard data"""
        try:
            from benny_trader import BennyTrader

            dashboard = BennyTrader.get_dashboard_data()
            return self.success_response(dashboard)
        except Exception as e:
            return self.error_response(f"Error fetching Benny dashboard: {str(e)}", 500)


# Lambda handler entry point
handler = MiscHandler()
lambda_handler = handler.lambda_handler

# Backward compatibility functions for tests
def handle_health():
    return handler.get_health()

def handle_get_benny_dashboard():
    return handler.get_benny_dashboard()

def handle_compliance_log(body: Dict[str, Any]):
    return handler.log_compliance(body)
