import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as iam from 'aws-cdk-lib/aws-iam';
import { SqsEventSource } from 'aws-cdk-lib/aws-lambda-event-sources';
import { Construct } from 'constructs';

export interface NotificationStackProps extends cdk.StackProps {
  environment: string;
}

export class NotificationStack extends cdk.Stack {
  public readonly notificationQueue: sqs.Queue;
  public readonly notificationProcessor: lambda.Function;

  constructor(scope: Construct, id: string, props: NotificationStackProps) {
    super(scope, id, props);

    const { environment } = props;

    // Dead letter queue for failed notifications
    const dlq = new sqs.Queue(this, 'NotificationDLQ', {
      queueName: `bet-notifications-dlq-${environment}`,
      retentionPeriod: cdk.Duration.days(14),
    });

    // SQS Queue for notification events
    this.notificationQueue = new sqs.Queue(this, 'NotificationQueue', {
      queueName: `bet-notifications-${environment}`,
      visibilityTimeout: cdk.Duration.seconds(30),
      retentionPeriod: cdk.Duration.days(1),
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: 3,
      },
    });

    // Notification processor Lambda
    this.notificationProcessor = new lambda.Function(this, 'NotificationProcessor', {
      functionName: `notification-processor-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'notification_processor.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.seconds(30),
      environment: {
        BENNY_NOTIFICATION_EMAIL: 'glogankaranovich@gmail.com',
        NOTIFICATION_FROM_EMAIL: 'noreply@carpoolbets.com',
      },
    });

    // Grant SES send permissions
    this.notificationProcessor.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail', 'ses:SendRawEmail'],
      resources: ['*'],
    }));

    // SQS trigger for processor
    this.notificationProcessor.addEventSource(new SqsEventSource(this.notificationQueue, {
      batchSize: 10,
    }));

    // Outputs
    new cdk.CfnOutput(this, 'NotificationQueueUrl', {
      value: this.notificationQueue.queueUrl,
      description: 'Notification queue URL',
    });

    new cdk.CfnOutput(this, 'NotificationQueueArn', {
      value: this.notificationQueue.queueArn,
      description: 'Notification queue ARN',
    });

    new cdk.CfnOutput(this, 'NotificationProcessorArn', {
      value: this.notificationProcessor.functionArn,
      description: 'Notification processor Lambda ARN',
    });
  }
}
