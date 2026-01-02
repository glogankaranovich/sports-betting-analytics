import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface PredictionGeneratorStackProps extends cdk.StackProps {
  betsTable: dynamodb.Table;
  environment: string;
}

export class PredictionGeneratorStack extends cdk.Stack {
  public readonly predictionGeneratorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: PredictionGeneratorStackProps) {
    super(scope, id, props);

    // Prediction Generator Lambda Function
    this.predictionGeneratorFunction = new lambda.Function(this, 'PredictionGeneratorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'prediction_generator.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTable.tableName,
        ENVIRONMENT: props.environment
      }
    });

    // Grant DynamoDB permissions
    props.betsTable.grantReadWriteData(this.predictionGeneratorFunction);

    // Schedule NBA game predictions (consensus model) every 6 hours
    const nbaGamePredictionsRule = new events.Rule(this, 'NBAGamePredictionsSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '6,12,18,0' })
    });
    nbaGamePredictionsRule.addTarget(new targets.LambdaFunction(this.predictionGeneratorFunction, {
      event: events.RuleTargetInput.fromObject({ 
        sport: 'basketball_nba', 
        bet_type: 'games', 
        model: 'consensus' 
      })
    }));

    // Schedule NBA prop predictions (consensus model) every 6 hours (offset by 1 hour)
    const nbaPropPredictionsRule = new events.Rule(this, 'NBAPropPredictionsSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '7,13,19,1' })
    });
    nbaPropPredictionsRule.addTarget(new targets.LambdaFunction(this.predictionGeneratorFunction, {
      event: events.RuleTargetInput.fromObject({ 
        sport: 'basketball_nba', 
        bet_type: 'props', 
        model: 'consensus' 
      })
    }));

    // Schedule NFL game predictions (consensus model) every 6 hours (offset by 2 hours)
    const nflGamePredictionsRule = new events.Rule(this, 'NFLGamePredictionsSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '8,14,20,2' })
    });
    nflGamePredictionsRule.addTarget(new targets.LambdaFunction(this.predictionGeneratorFunction, {
      event: events.RuleTargetInput.fromObject({ 
        sport: 'americanfootball_nfl', 
        bet_type: 'games', 
        model: 'consensus' 
      })
    }));

    // Schedule NFL prop predictions (consensus model) every 6 hours (offset by 3 hours)
    const nflPropPredictionsRule = new events.Rule(this, 'NFLPropPredictionsSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '9,15,21,3' })
    });
    nflPropPredictionsRule.addTarget(new targets.LambdaFunction(this.predictionGeneratorFunction, {
      event: events.RuleTargetInput.fromObject({ 
        sport: 'americanfootball_nfl', 
        bet_type: 'props', 
        model: 'consensus' 
      })
    }));

    // Output the function ARN for reference
    new cdk.CfnOutput(this, 'PredictionGeneratorFunctionArn', {
      value: this.predictionGeneratorFunction.functionArn,
      description: 'Prediction Generator Lambda Function ARN'
    });
  }
}
