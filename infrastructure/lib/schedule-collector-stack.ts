import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';
import { getSupportedSportsArray } from './utils/constants';

export interface ScheduleCollectorStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
}

export class ScheduleCollectorStack extends cdk.Stack {
  public readonly scheduleCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: ScheduleCollectorStackProps) {
    super(scope, id, props);

    this.scheduleCollectorFunction = new lambda.Function(this, 'ScheduleCollectorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'schedule_collector.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ENVIRONMENT: props.environment
      }
    });

    this.scheduleCollectorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:PutItem',
        'dynamodb:Query'
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`
      ]
    }));

    // Run daily at 6 AM ET (11 AM UTC) to collect schedules
    const sports = getSupportedSportsArray();
    
    sports.forEach((sport, index) => {
      const hour = 11 + Math.floor(index / 6); // Increment hour every 6 sports
      const minute = (index % 6) * 10; // 0, 10, 20, 30, 40, 50
      
      new events.Rule(this, `Daily${sport.split('_')[1].toUpperCase()}ScheduleCollection`, {
        schedule: events.Schedule.cron({
          minute: `${minute}`,
          hour: `${hour}`
        }),
        description: `Collect ${sport} schedules daily at ${hour}:${minute < 10 ? '0' : ''}${minute} UTC`,
        targets: [new targets.LambdaFunction(this.scheduleCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport })
        })]
      });
    });

    new cdk.CfnOutput(this, 'ScheduleCollectorFunctionArn', {
      value: this.scheduleCollectorFunction.functionArn
    });
  }
}
