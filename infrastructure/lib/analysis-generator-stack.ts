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
  public readonly analysisGeneratorNBA: lambda.Function;
  public readonly analysisGeneratorNFL: lambda.Function;
  public readonly analysisGeneratorMLB: lambda.Function;
  public readonly analysisGeneratorNHL: lambda.Function;
  public readonly analysisGeneratorEPL: lambda.Function;

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

    const policy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:Scan', 'dynamodb:Query', 'dynamodb:GetItem', 'dynamodb:PutItem', 'dynamodb:UpdateItem'],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    });

    // Create one Lambda per sport (12 rules each: 6 models × 2 bet types)
    this.analysisGeneratorNBA = new lambda.Function(this, 'AnalysisGeneratorNBA', {
      ...functionProps,
      functionName: `analysis-generator-nba-${props.environment}`
    });
    this.analysisGeneratorNBA.addToRolePolicy(policy);
    
    this.analysisGeneratorNFL = new lambda.Function(this, 'AnalysisGeneratorNFL', {
      ...functionProps,
      functionName: `analysis-generator-nfl-${props.environment}`
    });
    this.analysisGeneratorNFL.addToRolePolicy(policy);
    
    this.analysisGeneratorMLB = new lambda.Function(this, 'AnalysisGeneratorMLB', {
      ...functionProps,
      functionName: `analysis-generator-mlb-${props.environment}`
    });
    this.analysisGeneratorMLB.addToRolePolicy(policy);
    
    this.analysisGeneratorNHL = new lambda.Function(this, 'AnalysisGeneratorNHL', {
      ...functionProps,
      functionName: `analysis-generator-nhl-${props.environment}`
    });
    this.analysisGeneratorNHL.addToRolePolicy(policy);
    
    this.analysisGeneratorEPL = new lambda.Function(this, 'AnalysisGeneratorEPL', {
      ...functionProps,
      functionName: `analysis-generator-epl-${props.environment}`
    });
    this.analysisGeneratorEPL.addToRolePolicy(policy);
    
    // Create EventBridge rules
    const sports = [
      { key: 'basketball_nba', name: 'NBA', lambda: this.analysisGeneratorNBA },
      { key: 'americanfootball_nfl', name: 'NFL', lambda: this.analysisGeneratorNFL },
      { key: 'baseball_mlb', name: 'MLB', lambda: this.analysisGeneratorMLB },
      { key: 'icehockey_nhl', name: 'NHL', lambda: this.analysisGeneratorNHL },
      { key: 'soccer_epl', name: 'EPL', lambda: this.analysisGeneratorEPL }
    ];
    
    const models = ['consensus', 'value', 'momentum', 'contrarian', 'hot_cold', 'rest_schedule'];
    
    sports.forEach(sport => {
      models.forEach((model, index) => {
        new events.Rule(this, `Daily${sport.name}${model.charAt(0).toUpperCase() + model.slice(1)}GameAnalysis`, {
          schedule: events.Schedule.cron({ minute: `${index * 2}`, hour: '0' }),
          description: `Generate ${model} ${sport.name} game analyses at 7:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET`,
          targets: [new targets.LambdaFunction(sport.lambda, {
            event: events.RuleTargetInput.fromObject({ model, bet_type: 'games', sport: sport.key })
          })]
        });

        new events.Rule(this, `Daily${sport.name}${model.charAt(0).toUpperCase() + model.slice(1)}PropAnalysis`, {
          schedule: events.Schedule.cron({ minute: `${10 + (index * 2)}`, hour: '0' }),
          description: `Generate ${model} ${sport.name} prop analyses at 7:${10 + (index * 2)} PM ET`,
          targets: [new targets.LambdaFunction(sport.lambda, {
            event: events.RuleTargetInput.fromObject({ model, bet_type: 'props', sport: sport.key })
          })]
        });
      });
    });
  }
}
