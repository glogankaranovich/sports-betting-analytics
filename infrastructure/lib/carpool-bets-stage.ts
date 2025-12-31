import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DynamoDBStack } from './dynamodb-stack';
import { OddsCollectorStack } from './odds-collector-stack';
import { BetCollectorApiStack } from './bet-collector-api-stack';
import { IntegrationTestRoleStack } from './integration-test-role-stack';

export interface CarpoolBetsStageProps extends cdk.StageProps {
  stage: string;
}

export class CarpoolBetsStage extends cdk.Stage {
  public readonly betsTableName: cdk.CfnOutput;
  public readonly betCollectorApiUrl: cdk.CfnOutput;

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

    // Bet collector API stack
    const betCollectorApiStack = new BetCollectorApiStack(this, 'BetCollectorApi', {
      environment: props.stage,
      betsTableName: `carpool-bets-${props.stage}`,
    });

    // Integration test role for pipeline access
    new IntegrationTestRoleStack(this, 'IntegrationTestRole', {
      pipelineAccountId: '083314012659', // Pipeline account ID
    });

    // Export outputs for integration tests
    this.betsTableName = dynamoStack.betsTableName;
    this.betCollectorApiUrl = betCollectorApiStack.apiUrl;
  }
}
