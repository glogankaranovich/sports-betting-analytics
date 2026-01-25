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
  public readonly insightGeneratorNBA: lambda.Function;
  public readonly insightGeneratorNFL: lambda.Function;
  public readonly insightGeneratorMLB: lambda.Function;
  public readonly insightGeneratorNHL: lambda.Function;
  public readonly insightGeneratorEPL: lambda.Function;

  constructor(scope: Construct, id: string, props: InsightGeneratorStackProps) {
    super(scope, id, props);

    const functionProps = {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'insight_generator.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: ['bash', '-c', 'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'],
        },
      }),
      environment: { DYNAMODB_TABLE: props.betsTable.tableName },
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
    };

    // Create one Lambda per sport (12 rules each: 6 models × 2 bet types)
    this.insightGeneratorNBA = new lambda.Function(this, 'InsightGeneratorNBA', {
      ...functionProps,
      functionName: `insight-generator-nba-${props.environment}`
    });
    props.betsTable.grantReadWriteData(this.insightGeneratorNBA);
    
    this.insightGeneratorNFL = new lambda.Function(this, 'InsightGeneratorNFL', {
      ...functionProps,
      functionName: `insight-generator-nfl-${props.environment}`
    });
    props.betsTable.grantReadWriteData(this.insightGeneratorNFL);
    
    this.insightGeneratorMLB = new lambda.Function(this, 'InsightGeneratorMLB', {
      ...functionProps,
      functionName: `insight-generator-mlb-${props.environment}`
    });
    props.betsTable.grantReadWriteData(this.insightGeneratorMLB);
    
    this.insightGeneratorNHL = new lambda.Function(this, 'InsightGeneratorNHL', {
      ...functionProps,
      functionName: `insight-generator-nhl-${props.environment}`
    });
    props.betsTable.grantReadWriteData(this.insightGeneratorNHL);
    
    this.insightGeneratorEPL = new lambda.Function(this, 'InsightGeneratorEPL', {
      ...functionProps,
      functionName: `insight-generator-epl-${props.environment}`
    });
    props.betsTable.grantReadWriteData(this.insightGeneratorEPL);
    
    // Create EventBridge rules
    const sports = [
      { key: 'basketball_nba', name: 'NBA', lambda: this.insightGeneratorNBA },
      { key: 'americanfootball_nfl', name: 'NFL', lambda: this.insightGeneratorNFL },
      { key: 'baseball_mlb', name: 'MLB', lambda: this.insightGeneratorMLB },
      { key: 'icehockey_nhl', name: 'NHL', lambda: this.insightGeneratorNHL },
      { key: 'soccer_epl', name: 'EPL', lambda: this.insightGeneratorEPL }
    ];
    
    const models = ['consensus', 'value', 'momentum', 'contrarian', 'hot_cold', 'rest_schedule'];
    
    sports.forEach(sport => {
      models.forEach((model, index) => {
        new events.Rule(this, `Daily${sport.name}${model.charAt(0).toUpperCase() + model.slice(1)}GameInsight`, {
          schedule: events.Schedule.cron({ minute: `${index * 2}`, hour: '1' }),
          description: `Generate ${model} ${sport.name} game insights at 8:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET`,
          targets: [new targets.LambdaFunction(sport.lambda, {
            event: events.RuleTargetInput.fromObject({ model, analysis_type: 'game', sport: sport.key })
          })]
        });

        new events.Rule(this, `Daily${sport.name}${model.charAt(0).toUpperCase() + model.slice(1)}PropInsight`, {
          schedule: events.Schedule.cron({ minute: `${10 + (index * 2)}`, hour: '1' }),
          description: `Generate ${model} ${sport.name} prop insights at 8:${10 + (index * 2)} PM ET`,
          targets: [new targets.LambdaFunction(sport.lambda, {
            event: events.RuleTargetInput.fromObject({ model, analysis_type: 'prop', sport: sport.key })
          })]
        });
      });
    });
  }
}
