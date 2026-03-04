import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface BennyWeeklyReporterStackProps extends cdk.StackProps {
  environment: string;
  betsTable: dynamodb.ITable;
  frontendUrl: string;
  fromEmail: string;
  adminEmail?: string;
}

export class BennyWeeklyReporterStack extends cdk.Stack {
  public readonly weeklyReporterFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: BennyWeeklyReporterStackProps) {
    super(scope, id, props);

    // Lambda function for weekly report generation
    this.weeklyReporterFunction = new lambda.Function(this, 'BennyWeeklyReporterFunction', {
      functionName: `${id}-BennyWeeklyReporter`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'benny_weekly_reporter.lambda_handler',
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
        DYNAMODB_TABLE: props.betsTable.tableName,
        ENVIRONMENT: props.environment,
        FRONTEND_URL: props.frontendUrl,
        FROM_EMAIL: props.fromEmail,
        ...(props.adminEmail && { ADMIN_EMAIL: props.adminEmail }),
      },
    });

    // Grant DynamoDB read permissions
    props.betsTable.grantReadData(this.weeklyReporterFunction);
    
    this.weeklyReporterFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['dynamodb:Query'],
      resources: [
        `${props.betsTable.tableArn}/index/*`
      ],
    }));

    // Grant SES permissions
    this.weeklyReporterFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: [
        'ses:SendEmail',
        'ses:SendRawEmail'
      ],
      resources: ['*'],
    }));

    // EventBridge schedule - Every Monday at 9 AM ET (14:00 UTC)
    const weeklySchedule = new events.Rule(this, 'BennyWeeklyReportSchedule', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '14',
        weekDay: 'MON',
      }),
      description: 'Trigger Benny weekly report every Monday at 9 AM ET',
    });

    weeklySchedule.addTarget(new targets.LambdaFunction(this.weeklyReporterFunction));

    // EventBridge schedule - Every day at 8 AM ET (13:00 UTC)
    const dailySchedule = new events.Rule(this, 'BennyDailyReportSchedule', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '13',
      }),
      description: 'Trigger Benny daily report every day at 8 AM ET',
    });

    dailySchedule.addTarget(new targets.LambdaFunction(this.weeklyReporterFunction, {
      event: events.RuleTargetInput.fromObject({
        report_type: 'daily'
      })
    }));

    new cdk.CfnOutput(this, 'BennyWeeklyReporterFunctionName', {
      value: this.weeklyReporterFunction.functionName,
    });
  }
}
