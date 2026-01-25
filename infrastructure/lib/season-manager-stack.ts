import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface SeasonManagerStackProps extends cdk.StackProps {
  environment: string;
}

export class SeasonManagerStack extends cdk.Stack {
  public readonly seasonManagerFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: SeasonManagerStackProps) {
    super(scope, id, props);

    this.seasonManagerFunction = new lambda.Function(this, 'SeasonManagerFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'season_manager.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(5),
      memorySize: 256,
      environment: {
        ENVIRONMENT: props.environment
      }
    });

    this.seasonManagerFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'events:ListRules',
        'events:EnableRule',
        'events:DisableRule',
        'events:DescribeRule'
      ],
      resources: ['*']
    }));

    // Run on 1st of each month at 6 AM ET (11 AM UTC)
    new events.Rule(this, 'MonthlySeasonCheck', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '11',
        day: '1'
      }),
      description: 'Check and update sport season rules monthly',
      targets: [new targets.LambdaFunction(this.seasonManagerFunction)]
    });

    new cdk.CfnOutput(this, 'SeasonManagerFunctionArn', {
      value: this.seasonManagerFunction.functionArn
    });
  }
}
