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
  public readonly analysisGeneratorFunction2: lambda.Function;
  public readonly analysisGeneratorFunctionArn: cdk.CfnOutput;

  constructor(scope: Construct, id: string, props: AnalysisGeneratorStackProps) {
    super(scope, id, props);

    const functionProps = {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'analysis_generator.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ENVIRONMENT: props.environment
      }
    };

    this.analysisGeneratorFunction = new lambda.Function(this, 'AnalysisGeneratorFunction', {
      ...functionProps,
      functionName: `analysis-generator-1-${props.environment}`
    });
    this.analysisGeneratorFunction2 = new lambda.Function(this, 'AnalysisGeneratorFunction2', {
      ...functionProps,
      functionName: `analysis-generator-2-${props.environment}`
    });

    const policy = new iam.PolicyStatement({
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
    });

    this.analysisGeneratorFunction.addToRolePolicy(policy);
    this.analysisGeneratorFunction2.addToRolePolicy(policy);

    // EventBridge schedules to run daily at 7 PM ET (12 AM UTC) - after odds collection
    
    // Sport seasons - split between two Lambdas to avoid policy size limit
    const sportSeasons1 = {
      'basketball_nba': { start: 10, end: 6 },
      'americanfootball_nfl': { start: 9, end: 2 },
      'baseball_mlb': { start: 3, end: 10 }
    };
    
    const sportSeasons2 = {
      'icehockey_nhl': { start: 10, end: 6 },
      'soccer_epl': { start: 8, end: 5 }
    };
    
    const models = ['consensus', 'value', 'momentum', 'contrarian', 'hot_cold', 'rest_schedule'];
    
    // Lambda 1: NBA, NFL, MLB
    Object.entries(sportSeasons1).forEach(([sport, season]) => {
      const sportName = sport.split('_')[1].toUpperCase();
      
      models.forEach((model, index) => {
        new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}GameAnalysis`, {
          schedule: events.Schedule.cron({ minute: `${index * 2}`, hour: '0' }),
          description: `Generate ${model} ${sportName} game analyses at 7:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET`,
          targets: [new targets.LambdaFunction(this.analysisGeneratorFunction, {
            event: events.RuleTargetInput.fromObject({ model, bet_type: 'games', sport })
          })]
        });

        new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}PropAnalysis`, {
          schedule: events.Schedule.cron({ minute: `${10 + (index * 2)}`, hour: '0' }),
          description: `Generate ${model} ${sportName} prop analyses at 7:${10 + (index * 2)} PM ET`,
          targets: [new targets.LambdaFunction(this.analysisGeneratorFunction, {
            event: events.RuleTargetInput.fromObject({ model, bet_type: 'props', sport })
          })]
        });
      });
    });
    
    // Lambda 2: NHL, EPL
    Object.entries(sportSeasons2).forEach(([sport, season]) => {
      const sportName = sport.split('_')[1].toUpperCase();
      
      models.forEach((model, index) => {
        new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}GameAnalysis`, {
          schedule: events.Schedule.cron({ minute: `${index * 2}`, hour: '0' }),
          description: `Generate ${model} ${sportName} game analyses at 7:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET`,
          targets: [new targets.LambdaFunction(this.analysisGeneratorFunction2, {
            event: events.RuleTargetInput.fromObject({ model, bet_type: 'games', sport })
          })]
        });

        new events.Rule(this, `Daily${sportName}${model.charAt(0).toUpperCase() + model.slice(1)}PropAnalysis`, {
          schedule: events.Schedule.cron({ minute: `${10 + (index * 2)}`, hour: '0' }),
          description: `Generate ${model} ${sportName} prop analyses at 7:${10 + (index * 2)} PM ET`,
          targets: [new targets.LambdaFunction(this.analysisGeneratorFunction2, {
            event: events.RuleTargetInput.fromObject({ model, bet_type: 'props', sport })
          })]
        });
      });
    });

    this.analysisGeneratorFunctionArn = new cdk.CfnOutput(this, 'AnalysisGeneratorFunctionArn', {
      value: this.analysisGeneratorFunction.functionArn
    });
  }
}
