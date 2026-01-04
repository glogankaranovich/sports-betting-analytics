import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface RecommendationGeneratorStackProps extends cdk.StackProps {
  environment: string;
  dynamoDbTableName: string;
  dynamoDbTableArn: string;
}

export class RecommendationGeneratorStack extends cdk.Stack {
  public readonly recommendationGeneratorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: RecommendationGeneratorStackProps) {
    super(scope, id, props);

    // Lambda function for recommendation generation
    this.recommendationGeneratorFunction = new lambda.Function(this, 'RecommendationGeneratorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'recommendation_generator.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        exclude: ['tests/', '*.pyc', '__pycache__/', '.pytest_cache/']
      }),
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.dynamoDbTableName,
      },
    });

    // DynamoDB permissions
    this.recommendationGeneratorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Query',
        'dynamodb:Scan',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:DeleteItem',
        'dynamodb:BatchWriteItem'
      ],
      resources: [props.dynamoDbTableArn, `${props.dynamoDbTableArn}/index/*`]
    }));

    // EventBridge rule to trigger daily at 6 AM UTC
    const dailyRule = new events.Rule(this, 'DailyRecommendationGeneration', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '6',
        day: '*',
        month: '*',
        year: '*'
      }),
      description: 'Trigger recommendation generation daily at 6 AM UTC'
    });

    // Add Lambda as target
    dailyRule.addTarget(new targets.LambdaFunction(this.recommendationGeneratorFunction));

    // Output
    new cdk.CfnOutput(this, 'RecommendationGeneratorFunctionName', {
      value: this.recommendationGeneratorFunction.functionName,
      description: 'Recommendation Generator Lambda Function Name'
    });
  }
}
