import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface AnalysisGeneratorStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
}

export class AnalysisGeneratorStack extends cdk.Stack {
  public readonly analysisGeneratorFunction: lambda.Function;
  public readonly analysisGeneratorFunctionArn: cdk.CfnOutput;

  constructor(scope: Construct, id: string, props: AnalysisGeneratorStackProps) {
    super(scope, id, props);

    this.analysisGeneratorFunction = new lambda.Function(this, 'AnalysisGeneratorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'analysis_generator.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ENVIRONMENT: props.environment
      }
    });

    this.analysisGeneratorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Scan',
        'dynamodb:Query', 
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem'
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    }));

    // EventBridge schedules to run daily at 7 PM ET (12 AM UTC) - after odds collection
    
    // Sport seasons (month ranges)
    const sportSeasons = {
      'basketball_nba': { start: 10, end: 6 },      // Oct-Jun
      'americanfootball_nfl': { start: 9, end: 2 }, // Sep-Feb
      'baseball_mlb': { start: 3, end: 10 },        // Mar-Oct
      'icehockey_nhl': { start: 10, end: 6 },       // Oct-Jun
      'soccer_epl': { start: 8, end: 5 }            // Aug-May
    };
    
    const models = ['consensus', 'value', 'momentum', 'contrarian', 'hot_cold'];
    
    // Add single permission for all EventBridge rules to avoid policy size limit
    this.analysisGeneratorFunction.addPermission('AllowEventBridgeInvoke', {
      principal: new iam.ServicePrincipal('events.amazonaws.com'),
      action: 'lambda:InvokeFunction'
    });
    
    Object.entries(sportSeasons).forEach(([sport, season]) => {
      const sportName = sport.split('_')[1].toUpperCase();
      
      models.forEach((model, index) => {
        // Generate game analyses for each model/sport
        const gameRule = new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}GameAnalysis`, {
          schedule: events.Schedule.cron({
            minute: `${index * 2}`,
            hour: '0',
          }),
          description: `Generate ${model} ${sportName} game analyses at 7:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET (${season.start <= season.end ? `${season.start}-${season.end}` : `${season.start}-12,1-${season.end}`})`
        });

        gameRule.addTarget(new targets.LambdaFunction(this.analysisGeneratorFunction, {
          event: events.RuleTargetInput.fromObject({
            model: model,
            bet_type: 'games',
            sport: sport
          })
        }));

        // Generate prop analyses for each model/sport
        const propRule = new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}PropAnalysis`, {
          schedule: events.Schedule.cron({
            minute: `${10 + (index * 2)}`,
            hour: '0',
          }),
          description: `Generate ${model} ${sportName} prop analyses at 7:${10 + (index * 2)} PM ET (${season.start <= season.end ? `${season.start}-${season.end}` : `${season.start}-12,1-${season.end}`})`
        });

        propRule.addTarget(new targets.LambdaFunction(this.analysisGeneratorFunction, {
          event: events.RuleTargetInput.fromObject({
            model: model,
            bet_type: 'props',
            sport: sport
          })
        }));
      });
    });

    this.analysisGeneratorFunctionArn = new cdk.CfnOutput(this, 'AnalysisGeneratorFunctionArn', {
      value: this.analysisGeneratorFunction.functionArn
    });
  }
}
