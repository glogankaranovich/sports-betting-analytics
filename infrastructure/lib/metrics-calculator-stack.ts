import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface MetricsCalculatorStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
}

export class MetricsCalculatorStack extends cdk.Stack {
  public readonly metricsCalculatorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: MetricsCalculatorStackProps) {
    super(scope, id, props);

    // Lambda function for metrics calculation
    this.metricsCalculatorFunction = new lambda.Function(this, 'MetricsCalculatorFunction', {
      functionName: `metrics-calculator-${props.environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'metrics_calculator_handler.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(10),
      memorySize: 1024,
      environment: {
        DYNAMODB_TABLE: props.betsTableName
      }
    });

    // Grant permissions
    this.metricsCalculatorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:Query', 'dynamodb:PutItem', 'dynamodb:UpdateItem', 'dynamodb:GetItem'],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    }));

    // EventBridge rule - run daily at 6 AM UTC
    const rule = new events.Rule(this, 'MetricsCalculatorSchedule', {
      ruleName: `metrics-calculator-schedule-${props.environment}`,
      schedule: events.Schedule.cron({ hour: '6', minute: '0' }),
      description: 'Calculate opponent-adjusted metrics daily'
    });

    rule.addTarget(new targets.LambdaFunction(this.metricsCalculatorFunction));
  }
}
