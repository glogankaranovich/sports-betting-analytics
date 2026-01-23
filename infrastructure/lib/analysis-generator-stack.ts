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
    
    // Generate game analyses
    const dailyGameRule = new events.Rule(this, 'DailyGameAnalysisGeneration', {
      schedule: events.Schedule.cron({
        minute: '0',
        hour: '0',
      }),
      description: 'Generate game analyses daily at 7 PM ET'
    });

    dailyGameRule.addTarget(new targets.LambdaFunction(this.analysisGeneratorFunction, {
      event: events.RuleTargetInput.fromObject({
        model: 'consensus',
        bet_type: 'games'
      })
    }));

    // Generate prop analyses
    const dailyPropRule = new events.Rule(this, 'DailyPropAnalysisGeneration', {
      schedule: events.Schedule.cron({
        minute: '5',
        hour: '0',
      }),
      description: 'Generate prop analyses daily at 7:05 PM ET'
    });

    dailyPropRule.addTarget(new targets.LambdaFunction(this.analysisGeneratorFunction, {
      event: events.RuleTargetInput.fromObject({
        model: 'consensus',
        bet_type: 'props'
      })
    }));

    this.analysisGeneratorFunctionArn = new cdk.CfnOutput(this, 'AnalysisGeneratorFunctionArn', {
      value: this.analysisGeneratorFunction.functionArn
    });
  }
}
