import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface PlayerStatsCollectorStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
}

export class PlayerStatsCollectorStack extends cdk.Stack {
  public readonly playerStatsCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: PlayerStatsCollectorStackProps) {
    super(scope, id, props);

    // Lambda function for player stats collection
    this.playerStatsCollectorFunction = new lambda.Function(this, 'PlayerStatsCollectorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'player_stats_collector.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp *.py /asset-output/ && cp -r ml /asset-output/ 2>/dev/null || true'
          ]
        }
      }),
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
      }
    });

    // Grant DynamoDB permissions
    this.playerStatsCollectorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:GetItem'
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    }));

    // Output
    new cdk.CfnOutput(this, 'PlayerStatsCollectorFunctionArn', {
      value: this.playerStatsCollectorFunction.functionArn,
      description: 'Player Stats Collector Lambda Function ARN',
    });
  }
}
