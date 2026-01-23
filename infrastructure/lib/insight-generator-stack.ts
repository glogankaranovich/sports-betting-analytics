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
    
    // Generate insights for all models: consensus, value, momentum
    const models = ['consensus', 'value', 'momentum'];
    
    models.forEach((model, index) => {
      // Generate game insights for each model
      const gameRule = new events.Rule(this, `Daily${model.charAt(0).toUpperCase() + model.slice(1)}GameInsight`, {
        schedule: events.Schedule.cron({
          minute: `${index * 2}`,  // Stagger by 2 minutes: 0, 2, 4
          hour: '1',
        }),
        description: `Generate ${model} game insights daily at 8:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET`
      });

      gameRule.addTarget(new targets.LambdaFunction(this.insightGeneratorFunction, {
        event: events.RuleTargetInput.fromObject({
          model: model,
          analysis_type: 'game'
        })
      }));

      // Generate prop insights for each model
      const propRule = new events.Rule(this, `Daily${model.charAt(0).toUpperCase() + model.slice(1)}PropInsight`, {
        schedule: events.Schedule.cron({
          minute: `${10 + (index * 2)}`,  // Stagger by 2 minutes: 10, 12, 14
          hour: '1',
        }),
        description: `Generate ${model} prop insights daily at 8:${10 + (index * 2)} PM ET`
      });

      propRule.addTarget(new targets.LambdaFunction(this.insightGeneratorFunction, {
        event: events.RuleTargetInput.fromObject({
          model: model,
          analysis_type: 'prop'
        })
      }));
    });

    new cdk.CfnOutput(this, 'InsightGeneratorFunctionArn', {
      value: this.insightGeneratorFunction.functionArn,
    });
  }
}
