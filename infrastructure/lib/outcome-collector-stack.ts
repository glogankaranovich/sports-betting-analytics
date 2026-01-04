import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface OutcomeCollectorStackProps extends cdk.StackProps {
  environment: string;
  dynamoDbTableName: string;
  dynamoDbTableArn: string;
  oddsApiSecretArn: string;
}

export class OutcomeCollectorStack extends cdk.Stack {
  public readonly outcomeCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: OutcomeCollectorStackProps) {
    super(scope, id, props);

    // Lambda function for outcome collection
    this.outcomeCollectorFunction = new lambda.Function(this, 'OutcomeCollectorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'outcome_collector.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        exclude: ['tests/', '*.pyc', '__pycache__/', '.pytest_cache/']
      }),
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.dynamoDbTableName,
        ODDS_API_SECRET_ARN: props.oddsApiSecretArn,
      },
    });

    // DynamoDB permissions
    this.outcomeCollectorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Query',
        'dynamodb:Scan',
        'dynamodb:UpdateItem',
        'dynamodb:BatchWriteItem'
      ],
      resources: [props.dynamoDbTableArn, `${props.dynamoDbTableArn}/index/*`]
    }));

    // Secrets Manager permissions
    this.outcomeCollectorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['secretsmanager:GetSecretValue'],
      resources: [props.oddsApiSecretArn]
    }));

    // EventBridge rule to trigger daily at 8 AM UTC (after games complete)
    const dailyRule = new events.Rule(this, 'DailyOutcomeCollection', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '8',
        day: '*',
        month: '*',
        year: '*'
      }),
      description: 'Trigger outcome collection daily at 8 AM UTC'
    });

    // Add Lambda as target
    dailyRule.addTarget(new targets.LambdaFunction(this.outcomeCollectorFunction));

    // Output
    new cdk.CfnOutput(this, 'OutcomeCollectorFunctionName', {
      value: this.outcomeCollectorFunction.functionName,
      description: 'Outcome Collector Lambda Function Name'
    });
  }
}
