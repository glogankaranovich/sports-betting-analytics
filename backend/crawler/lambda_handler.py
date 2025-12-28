"""
Lambda handler entry point for AWS deployment.
"""

import json
import asyncio
import logging
from typing import Dict, Any

# Configure logging for Lambda
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    AWS Lambda entry point for data collection.
    
    Routes to async handler based on event structure.
    """
    try:
        # Import here to avoid cold start issues
        from scheduler import lambda_handler as async_handler
        
        # Run async handler
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(async_handler(event, context))
            
            # Return proper Lambda response
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps(result)
            }
            
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"Lambda handler failed: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__
            })
        }
