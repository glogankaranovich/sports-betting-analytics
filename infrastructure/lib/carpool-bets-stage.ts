import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DynamoDBStack } from './dynamodb-stack';
import { OddsCollectorStack } from './odds-collector-stack';

export interface CarpoolBetsStageProps extends cdk.StageProps {
  stage: string;
}

export class CarpoolBetsStage extends cdk.Stage {
  public readonly betsTableName: cdk.CfnOutput;

  constructor(scope: Construct, id: string, props: CarpoolBetsStageProps) {
    super(scope, id, props);

    // DynamoDB Stack
    const dynamoStack = new DynamoDBStack(this, 'DynamoDB', {
      environment: props.stage,
    });

    // Odds collector Lambda stack
    new OddsCollectorStack(this, 'OddsCollector', {
      environment: props.stage,
      betsTableName: `carpool-bets-${props.stage}`,
    });

    // Export outputs for integration tests
    this.betsTableName = dynamoStack.betsTableName;
  }
}
