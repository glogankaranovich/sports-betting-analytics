import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';
import { PLATFORM_CONSTANTS } from './utils/constants';

interface NewsCollectorsStackProps extends cdk.StackProps {
  environment: string;
  betsTable: dynamodb.ITable;
}

export class NewsCollectorsStack extends cdk.Stack {
  public readonly espnCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: NewsCollectorsStackProps) {
    super(scope, id, props);

    const { environment, betsTable } = props;

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
        TABLE_NAME: betsTable.tableName,
        ENVIRONMENT: environment,
        SUPPORTED_SPORTS: PLATFORM_CONSTANTS.SUPPORTED_SPORTS,
      },
    });

    // Grant DynamoDB permissions
    betsTable.grantReadWriteData(this.espnCollectorFunction);

    // Grant Comprehend permissions for sentiment analysis
    this.espnCollectorFunction.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ['comprehend:DetectSentiment'],
        resources: ['*'],
      })
    );

    // EventBridge Schedule: ESPN collector every 2 hours
    const espnRule = new events.Rule(this, 'ESPNCollectorSchedule', {
      ruleName: `espn-collector-schedule-${environment}`,
      schedule: events.Schedule.rate(cdk.Duration.hours(2)),
      description: 'Collect ESPN news every 2 hours',
    });

    espnRule.addTarget(new targets.LambdaFunction(this.espnCollectorFunction));

    // Outputs
    new cdk.CfnOutput(this, 'ESPNCollectorFunctionName', {
      value: this.espnCollectorFunction.functionName,
      description: 'ESPN Collector Lambda Function Name',
    });
  }
}
