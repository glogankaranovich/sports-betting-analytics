import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { getPlatformEnvironment } from './utils/constants';

interface ModelComparisonCacheStackProps extends cdk.StackProps {
  environment: string;
  tableName: string;
  tableArn: string;
}

export class ModelComparisonCacheStack extends cdk.Stack {
  public readonly cacheFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: ModelComparisonCacheStackProps) {
    super(scope, id, props);

    // Lambda function to pre-compute model comparison
    this.cacheFunction = new lambda.Function(this, 'ModelComparisonCacheFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'model_comparison_cache.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        exclude: ['tests', '__pycache__', '*.pyc', '.pytest_cache', 'venv'],
      }),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.tableName,
        ...getPlatformEnvironment(),
      },
      description: `Pre-compute model comparison data - ${props.environment}`,
    });

    // Grant DynamoDB permissions
    this.cacheFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'dynamodb:Query',
          'dynamodb:GetItem',
          'dynamodb:PutItem',
          'dynamodb:UpdateItem',
        ],
        resources: [
          props.tableArn,
          `${props.tableArn}/index/*`,
        ],
      })
    );

    // EventBridge rule to run every 15 minutes
    const rule = new events.Rule(this, 'ModelComparisonCacheSchedule', {
      schedule: events.Schedule.rate(cdk.Duration.minutes(15)),
      description: 'Trigger model comparison cache update every 15 minutes',
    });

    rule.addTarget(new targets.LambdaFunction(this.cacheFunction));

    // Outputs
    new cdk.CfnOutput(this, 'CacheFunctionArn', {
      value: this.cacheFunction.functionArn,
      description: 'Model Comparison Cache Function ARN',
    });
  }
}
