"""
Lambda function to forward SES emails to personal email
Receives emails at carpoolbets.com addresses and forwards to glogankaranovich@gmail.com
"""
import os

import boto3
from botocore.exceptions import ClientError

ses = boto3.client("ses", region_name="us-east-1")
s3 = boto3.client("s3")

FORWARD_TO = "glogankaranovich@gmail.com"
BUCKET = os.environ.get("EMAIL_BUCKET", "carpoolbets-emails")


def lambda_handler(event, context):
    """Forward incoming SES email"""
    try:
        record = event["Records"][0]
        message = record["ses"]["mail"]
        message_id = message["messageId"]
        recipient = record["ses"]["receipt"]["recipients"][0]

        # Get email from S3
        obj = s3.get_object(Bucket=BUCKET, Key=message_id)
        raw_email = obj["Body"].read()

        # Forward email
        ses.send_raw_email(
            Source="noreply@carpoolbets.com",
            Destinations=[FORWARD_TO],
            RawMessage={"Data": raw_email},
            Tags=[{"Name": "OriginalRecipient", "Value": recipient}],
        )

        print(f"Forwarded email from {recipient} to {FORWARD_TO}")
        return {"statusCode": 200}

    except ClientError as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        
        # Emit CloudWatch metric
        try:
            cloudwatch = boto3.client('cloudwatch')
            cloudwatch.put_metric_data(
                Namespace='SportsAnalytics/EmailForwarder',
                MetricData=[{
                    'MetricName': 'ForwardError',
                    'Value': 1,
                    'Unit': 'Count'
                }]
            )
        except:
            pass
        
        return {"statusCode": 500, "body": str(e)}
