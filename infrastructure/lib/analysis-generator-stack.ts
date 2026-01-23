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
    
    // Generate analyses for all models: consensus, value, momentum
    const models = ['consensus', 'value', 'momentum'];
    
    models.forEach((model, index) => {
      // Generate game analyses for each model
      const gameRule = new events.Rule(this, `Daily${model.charAt(0).toUpperCase() + model.slice(1)}GameAnalysis`, {
        schedule: events.Schedule.cron({
          minute: `${index * 2}`,  // Stagger by 2 minutes: 0, 2, 4
          hour: '0',
        }),
        description: `Generate ${model} game analyses daily at 7:${index * 2 < 10 ? '0' : ''}${index * 2} PM ET`
      });

      gameRule.addTarget(new targets.LambdaFunction(this.analysisGeneratorFunction, {
        event: events.RuleTargetInput.fromObject({
          model: model,
          bet_type: 'games'
        })
      }));

      // Generate prop analyses for each model
      const propRule = new events.Rule(this, `Daily${model.charAt(0).toUpperCase() + model.slice(1)}PropAnalysis`, {
        schedule: events.Schedule.cron({
          minute: `${10 + (index * 2)}`,  // Stagger by 2 minutes: 10, 12, 14
          hour: '0',
        }),
        description: `Generate ${model} prop analyses daily at 7:${10 + (index * 2)} PM ET`
      });

      propRule.addTarget(new targets.LambdaFunction(this.analysisGeneratorFunction, {
        event: events.RuleTargetInput.fromObject({
          model: model,
          bet_type: 'props'
        })
      }));
    });

    this.analysisGeneratorFunctionArn = new cdk.CfnOutput(this, 'AnalysisGeneratorFunctionArn', {
      value: this.analysisGeneratorFunction.functionArn
    });
  }
}
