import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
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
  public readonly insightGeneratorFunction2: lambda.Function;

  constructor(scope: Construct, id: string, props: InsightGeneratorStackProps) {
    super(scope, id, props);

    const functionProps = {
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
    };

    // Split into 2 Lambdas by bet type to avoid IAM policy size limit
    // Lambda 1: Game insights (all sports) - 30 rules
    // Lambda 2: Prop insights (all sports) - 30 rules
    this.insightGeneratorFunction = new lambda.Function(this, 'InsightGeneratorFunction', functionProps);
    this.insightGeneratorFunction2 = new lambda.Function(this, 'InsightGeneratorFunction2', functionProps);

    props.betsTable.grantReadWriteData(this.insightGeneratorFunction);
    props.betsTable.grantReadWriteData(this.insightGeneratorFunction2);

    // EventBridge schedules to run daily at 8 PM ET (1 AM UTC) - after analysis generation
    
    // All sports
    const sports = {
      'basketball_nba': { start: 10, end: 6 },
      'americanfootball_nfl': { start: 9, end: 2 },
      'baseball_mlb': { start: 3, end: 10 },
      'icehockey_nhl': { start: 10, end: 6 },
      'soccer_epl': { start: 8, end: 5 }
    };
    
    const models = ['consensus', 'value', 'momentum', 'contrarian', 'hot_cold', 'rest_schedule'];
    
    // Lambda 1: Game insights for all sports (30 rules)
    Object.entries(sports).forEach(([sport, season]) => {
      const sportName = sport.split('_')[1].toUpperCase();
      
      models.forEach((model, index) => {
        new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}GameInsight`, {
          schedule: events.Schedule.cron({ minute: `${index * 2}`, hour: '1' }),
          description: `Generate ${model} ${sportName} game insights at 8:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET`,
          targets: [new targets.LambdaFunction(this.insightGeneratorFunction, {
            event: events.RuleTargetInput.fromObject({ model, analysis_type: 'game', sport })
          })]
        });
      });
    });
    
    // Lambda 2: Prop insights for all sports (30 rules)
    Object.entries(sports).forEach(([sport, season]) => {
      const sportName = sport.split('_')[1].toUpperCase();
      
      models.forEach((model, index) => {
        new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}PropInsight`, {
          schedule: events.Schedule.cron({ minute: `${10 + (index * 2)}`, hour: '1' }),
          description: `Generate ${model} ${sportName} prop insights at 8:${10 + (index * 2)} PM ET`,
          targets: [new targets.LambdaFunction(this.insightGeneratorFunction2, {
            event: events.RuleTargetInput.fromObject({ model, analysis_type: 'prop', sport })
          })]
        });
      });
    });

    new cdk.CfnOutput(this, 'InsightGeneratorFunctionArn', {
      value: this.insightGeneratorFunction.functionArn,
    });
  }
}
