import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

interface NewsCollectorsStackProps extends cdk.StackProps {
  environment: string;
  tableName: string;
  tableArn: string;
}

export class NewsCollectorsStack extends cdk.Stack {
  public readonly espnCollectorFunction: lambda.Function;
  public readonly redditCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: NewsCollectorsStackProps) {
    super(scope, id, props);

    const { environment, tableName, tableArn } = props;

    // ESPN News Collector Lambda
    this.espnCollectorFunction = new lambda.Function(this, 'ESPNCollectorFunction', {
      functionName: `espn-collector-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'espn_collector.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      environment: {
        TABLE_NAME: tableName,
        ENVIRONMENT: environment,
        SUPPORTED_SPORTS: 'basketball_nba,americanfootball_nfl,baseball_mlb,icehockey_nhl,soccer_epl',
      },
    });

    // Reddit Sentiment Collector Lambda
    this.redditCollectorFunction = new lambda.Function(this, 'RedditCollectorFunction', {
      functionName: `reddit-collector-${environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'reddit_collector.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install --no-cache -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      environment: {
        TABLE_NAME: tableName,
        ENVIRONMENT: environment,
        SUPPORTED_SPORTS: 'basketball_nba,americanfootball_nfl,baseball_mlb,icehockey_nhl,soccer_epl',
      },
    });

    // Grant DynamoDB permissions
    this.espnCollectorFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['dynamodb:PutItem', 'dynamodb:Query'],
        resources: [tableArn, `${tableArn}/index/*`],
      })
    );

    this.redditCollectorFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['dynamodb:PutItem', 'dynamodb:Query'],
        resources: [tableArn, `${tableArn}/index/*`],
      })
    );

    // Grant Comprehend permissions for Reddit collector
    this.redditCollectorFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          'comprehend:BatchDetectSentiment',
          'comprehend:BatchDetectEntities',
        ],
        resources: ['*'],
      })
    );

    // EventBridge Schedule: ESPN collector every 30 minutes
    const espnRule = new events.Rule(this, 'ESPNCollectorSchedule', {
      ruleName: `espn-collector-schedule-${environment}`,
      schedule: events.Schedule.rate(cdk.Duration.minutes(30)),
      description: 'Collect ESPN news every 30 minutes',
    });

    espnRule.addTarget(new targets.LambdaFunction(this.espnCollectorFunction));

    // EventBridge Schedule: Reddit collector every 15 minutes
    const redditRule = new events.Rule(this, 'RedditCollectorSchedule', {
      ruleName: `reddit-collector-schedule-${environment}`,
      schedule: events.Schedule.rate(cdk.Duration.minutes(15)),
      description: 'Collect Reddit sentiment every 15 minutes',
    });

    redditRule.addTarget(new targets.LambdaFunction(this.redditCollectorFunction));

    // Outputs
    new cdk.CfnOutput(this, 'ESPNCollectorFunctionName', {
      value: this.espnCollectorFunction.functionName,
      description: 'ESPN Collector Lambda Function Name',
    });

    new cdk.CfnOutput(this, 'RedditCollectorFunctionName', {
      value: this.redditCollectorFunction.functionName,
      description: 'Reddit Collector Lambda Function Name',
    });
  }
}
