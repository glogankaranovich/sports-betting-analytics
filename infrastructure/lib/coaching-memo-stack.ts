import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface CoachingMemoStackProps extends cdk.StackProps {
  environment: string;
  betsTable: dynamodb.ITable;
}

export class CoachingMemoStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: CoachingMemoStackProps) {
    super(scope, id, props);

    const fn = new lambda.Function(this, 'CoachingMemoFunction', {
      functionName: `${id}-CoachingMemo`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'coaching_memo_generator.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.minutes(3),
      memorySize: 256,
      environment: {
        BETS_TABLE: props.betsTable.tableName,
        ENVIRONMENT: props.environment,
      },
    });

    props.betsTable.grantReadWriteData(fn);

    fn.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: ['*'],
    }));

    // Daily at 8:30 AM ET (13:30 UTC) — after outcome collector settles overnight games
    new events.Rule(this, 'DailyCoachingMemoSchedule', {
      schedule: events.Schedule.cron({ minute: '30', hour: '13' }),
      description: 'Daily coaching memo generation for Benny models',
    }).addTarget(new targets.LambdaFunction(fn));

    new cdk.CfnOutput(this, 'CoachingMemoFunctionName', {
      value: fn.functionName,
    });
  }
}
