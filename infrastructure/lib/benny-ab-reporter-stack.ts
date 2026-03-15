import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface BennyABReporterStackProps extends cdk.StackProps {
  environment: string;
  betsTable: dynamodb.ITable;
}

export class BennyABReporterStack extends cdk.Stack {
  public readonly abReporterFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: BennyABReporterStackProps) {
    super(scope, id, props);

    this.abReporterFunction = new lambda.Function(this, 'BennyABReporterFunction', {
      functionName: `${id}-BennyABReporter`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'benny_ab_reporter.handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.minutes(2),
      memorySize: 256,
      environment: {
        BETS_TABLE: props.betsTable.tableName,
        ENVIRONMENT: props.environment,
      },
    });

    props.betsTable.grantReadData(this.abReporterFunction);

    this.abReporterFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['ses:SendEmail'],
      resources: ['*'],
    }));

    // Daily at 8 AM ET (13:00 UTC)
    const dailySchedule = new events.Rule(this, 'BennyABReportSchedule', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '13',
      }),
      description: 'Daily A/B comparison report at 8 AM ET',
    });

    dailySchedule.addTarget(new targets.LambdaFunction(this.abReporterFunction));

    new cdk.CfnOutput(this, 'BennyABReporterFunctionName', {
      value: this.abReporterFunction.functionName,
    });
  }
}
