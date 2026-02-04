import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
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

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during NBA season (Oct-Jun)
    const dailyNbaRule = new events.Rule(this, 'DailyNbaStatsCollection', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '7',
        month: '10-6',
      }),
      description: 'Collect NBA player stats daily at 2 AM ET during NBA season'
    });

    dailyNbaRule.addTarget(new targets.LambdaFunction(this.playerStatsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'basketball_nba' })
    }));

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during NFL season (Sep-Feb)
    const dailyNflRule = new events.Rule(this, 'DailyNflStatsCollection', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '7',
        month: '9-2',
      }),
      description: 'Collect NFL player stats daily at 2 AM ET during NFL season'
    });

    dailyNflRule.addTarget(new targets.LambdaFunction(this.playerStatsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'americanfootball_nfl' })
    }));

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during MLB season (Mar-Oct)
    const dailyMlbRule = new events.Rule(this, 'DailyMlbStatsCollection', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '7',
        month: '3-10',
      }),
      description: 'Collect MLB player stats daily at 2 AM ET during MLB season'
    });

    dailyMlbRule.addTarget(new targets.LambdaFunction(this.playerStatsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'baseball_mlb' })
    }));

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during NHL season (Oct-Jun)
    const dailyNhlRule = new events.Rule(this, 'DailyNhlStatsCollection', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '7',
        month: '10-6',
      }),
      description: 'Collect NHL player stats daily at 2 AM ET during NHL season'
    });

    dailyNhlRule.addTarget(new targets.LambdaFunction(this.playerStatsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'icehockey_nhl' })
    }));

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during EPL season (Aug-May)
    const dailyEplRule = new events.Rule(this, 'DailyEplStatsCollection', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '7',
        month: '8-5',
      }),
      description: 'Collect EPL player stats daily at 2 AM ET during EPL season'
    });

    dailyEplRule.addTarget(new targets.LambdaFunction(this.playerStatsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'soccer_epl' })
    }));

    // Output
    new cdk.CfnOutput(this, 'PlayerStatsCollectorFunctionArn', {
      value: this.playerStatsCollectorFunction.functionArn,
      description: 'Player Stats Collector Lambda Function ARN',
    });
  }
}
