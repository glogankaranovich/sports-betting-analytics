"""
Lambda function to generate predictions on schedule
"""

import json
import os
from prediction_tracker import PredictionTracker

def lambda_handler(event, context):
    """Generate and store predictions for all games"""
    
    table_name = os.getenv('DYNAMODB_TABLE')
    if not table_name:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'DYNAMODB_TABLE environment variable not set'})
        }
    
    try:
        tracker = PredictionTracker(table_name)
        predictions_count = tracker.generate_and_store_predictions()
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': f'Generated and stored {predictions_count} predictions',
                'predictions_count': predictions_count
            })
        }
        
    except Exception as e:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': f'Failed to generate predictions: {str(e)}'})
        }
