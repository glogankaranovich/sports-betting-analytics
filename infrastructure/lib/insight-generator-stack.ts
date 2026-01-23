import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface InsightGeneratorStackProps extends cdk.StackProps {
  environment: string;
  betsTable: dynamodb.ITable;
}

export class InsightGeneratorStack extends cdk.Stack {
  public readonly insightGeneratorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: InsightGeneratorStackProps) {
    super(scope, id, props);

    this.insightGeneratorFunction = new lambda.Function(this, 'InsightGeneratorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'insight_generator.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      environment: {
        DYNAMODB_TABLE: props.betsTable.tableName,
      },
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
    });

    props.betsTable.grantReadWriteData(this.insightGeneratorFunction);

    // EventBridge schedules to run daily at 8 PM ET (1 AM UTC) - after analysis generation
    
    // Generate game insights
    const dailyGameRule = new events.Rule(this, 'DailyGameInsightGeneration', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '1',
      }),
      description: 'Generate game insights daily at 8 PM ET'
    });

    dailyGameRule.addTarget(new targets.LambdaFunction(this.insightGeneratorFunction, {
      event: events.RuleTargetInput.fromObject({
        model: 'consensus',
        analysis_type: 'game'
      })
    }));

    // Generate prop insights
    const dailyPropRule = new events.Rule(this, 'DailyPropInsightGeneration', {
      schedule: events.Schedule.cron({
        minute: '5',
        hour: '1',
      }),
      description: 'Generate prop insights daily at 8:05 PM ET'
    });

    dailyPropRule.addTarget(new targets.LambdaFunction(this.insightGeneratorFunction, {
      event: events.RuleTargetInput.fromObject({
        model: 'consensus',
        analysis_type: 'prop'
      })
    }));

    new cdk.CfnOutput(this, 'InsightGeneratorFunctionArn', {
      value: this.insightGeneratorFunction.functionArn,
    });
  }
}
