import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface InjuryCollectorStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
}

export class InjuryCollectorStack extends cdk.Stack {
  public readonly injuryCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: InjuryCollectorStackProps) {
    super(scope, id, props);

    this.injuryCollectorFunction = new lambda.Function(this, 'InjuryCollectorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'injury_collector.lambda_handler',
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

    this.injuryCollectorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:PutItem',
        'dynamodb:UpdateItem',
        'dynamodb:Query',
        'dynamodb:GetItem'
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    }));

    // NBA injuries - daily at 1 AM ET (6 AM UTC) during season (Oct-Jun)
    new events.Rule(this, 'DailyNbaInjuryCollection', {
      schedule: events.Schedule.cron({ minute: '0', hour: '6', month: '10-6' }),
      description: 'Collect NBA injury reports daily at 1 AM ET',
      targets: [new targets.LambdaFunction(this.injuryCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: 'basketball_nba' })
      })]
    });

    // NFL injuries - daily at 1 AM ET (6 AM UTC) during season (Sep-Feb)
    new events.Rule(this, 'DailyNflInjuryCollection', {
      schedule: events.Schedule.cron({ minute: '0', hour: '6', month: '9-2' }),
      description: 'Collect NFL injury reports daily at 1 AM ET',
      targets: [new targets.LambdaFunction(this.injuryCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: 'americanfootball_nfl' })
      })]
    });

    // MLB injuries - daily at 1 AM ET (6 AM UTC) during season (Mar-Oct)
    new events.Rule(this, 'DailyMlbInjuryCollection', {
      schedule: events.Schedule.cron({ minute: '0', hour: '6', month: '3-10' }),
      description: 'Collect MLB injury reports daily at 1 AM ET',
      targets: [new targets.LambdaFunction(this.injuryCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: 'baseball_mlb' })
      })]
    });

    // NHL injuries - daily at 1 AM ET (6 AM UTC) during season (Oct-Jun)
    new events.Rule(this, 'DailyNhlInjuryCollection', {
      schedule: events.Schedule.cron({ minute: '0', hour: '6', month: '10-6' }),
      description: 'Collect NHL injury reports daily at 1 AM ET',
      targets: [new targets.LambdaFunction(this.injuryCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: 'icehockey_nhl' })
      })]
    });

    // EPL injuries - daily at 1 AM ET (6 AM UTC) during season (Aug-May)
    new events.Rule(this, 'DailyEplInjuryCollection', {
      schedule: events.Schedule.cron({ minute: '0', hour: '6', month: '8-5' }),
      description: 'Collect EPL injury reports daily at 1 AM ET',
      targets: [new targets.LambdaFunction(this.injuryCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: 'soccer_epl' })
      })]
    });

    new cdk.CfnOutput(this, 'InjuryCollectorFunctionArn', {
      value: this.injuryCollectorFunction.functionArn,
      description: 'Injury Collector Lambda Function ARN',
    });
  }
}
