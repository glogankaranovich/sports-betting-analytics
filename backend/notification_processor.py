"""
Notification processor Lambda - processes notification events from SQS.
"""
import json
import os
import logging
from notification_service import NotificationService

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """Process notification events from SQS"""
    service = NotificationService()
    
    results = {
        'successful': 0,
        'failed': 0,
        'errors': []
    }
    
    for record in event['Records']:
        try:
            message = json.loads(record['body'])
            notification_type = message.get('type')
            data = message.get('data', {})
            
            if notification_type == 'bet_placed':
                formatted_message = service.format_bet_notification(data)

                # Discord (always)
                service.send_notification('discord', '', formatted_message, data)

                # Email
                email = os.environ.get('BENNY_NOTIFICATION_EMAIL')
                if not email:
                    logger.warning("BENNY_NOTIFICATION_EMAIL not set, skipping email")
                else:
                    success = service.send_notification('email', email, formatted_message, data)
                    if not success:
                        results['failed'] += 1
                        results['errors'].append(f"Failed to send email for {data.get('game')}")

                results['successful'] += 1

            elif notification_type == 'consensus_report':
                formatted_message = service.format_consensus_report(data)

                # Discord (always)
                service.send_notification('discord', '', formatted_message, data)

                # Email
                email = os.environ.get('BENNY_NOTIFICATION_EMAIL')
                if not email:
                    logger.warning("BENNY_NOTIFICATION_EMAIL not set, skipping email")
                else:
                    success = service.send_notification('email', email, formatted_message, data)
                    if not success:
                        results['failed'] += 1
                        results['errors'].append("Failed to send consensus report email")

                results['successful'] += 1
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
                
        except Exception as e:
            logger.error(f"Error processing notification: {str(e)}")
            results['failed'] += 1
            results['errors'].append(str(e))
    
    logger.info(f"Processed {results['successful']} successful, {results['failed']} failed notifications")
    
    return {
        'statusCode': 200,
        'body': json.dumps(results)
    }
