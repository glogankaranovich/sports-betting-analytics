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
    
    // Sport seasons (month ranges)
    const sportSeasons = {
      'basketball_nba': { start: 10, end: 6 },      // Oct-Jun
      'americanfootball_nfl': { start: 9, end: 2 }, // Sep-Feb
      'baseball_mlb': { start: 3, end: 10 },        // Mar-Oct
      'icehockey_nhl': { start: 10, end: 6 },       // Oct-Jun
      'soccer_epl': { start: 8, end: 5 }            // Aug-May
    };
    
    const models = ['consensus', 'value', 'momentum', 'contrarian', 'hot_cold'];
    
    Object.entries(sportSeasons).forEach(([sport, season]) => {
      const sportName = sport.split('_')[1].toUpperCase();
      
      models.forEach((model, index) => {
        // Generate game insights for each model/sport
        const gameRule = new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}GameInsight`, {
          schedule: events.Schedule.cron({
            minute: `${index * 2}`,
            hour: '1',
          }),
          description: `Generate ${model} ${sportName} game insights at 8:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET (${season.start <= season.end ? `${season.start}-${season.end}` : `${season.start}-12,1-${season.end}`})`
        });

        gameRule.addTarget(new targets.LambdaFunction(this.insightGeneratorFunction, {
          event: events.RuleTargetInput.fromObject({
            model: model,
            analysis_type: 'game',
            sport: sport
          })
        }));

        // Generate prop insights for each model/sport
        const propRule = new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}PropInsight`, {
          schedule: events.Schedule.cron({
            minute: `${10 + (index * 2)}`,
            hour: '1',
          }),
          description: `Generate ${model} ${sportName} prop insights at 8:${10 + (index * 2)} PM ET (${season.start <= season.end ? `${season.start}-${season.end}` : `${season.start}-12,1-${season.end}`})`
        });

        propRule.addTarget(new targets.LambdaFunction(this.insightGeneratorFunction, {
          event: events.RuleTargetInput.fromObject({
            model: model,
            analysis_type: 'prop',
            sport: sport
          })
        }));
      });
    });

    new cdk.CfnOutput(this, 'InsightGeneratorFunctionArn', {
      value: this.insightGeneratorFunction.functionArn,
    });
  }
}
