import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DynamoDBStack } from './dynamodb-stack';
import { OddsCollectorStack } from './odds-collector-stack';
import { BetCollectorApiStack } from './bet-collector-api-stack';
import { PredictionGeneratorStack } from './prediction-generator-stack';
import { RecommendationGeneratorStack } from './recommendation-generator-stack';
import { OutcomeCollectorStack } from './outcome-collector-stack';
import { AuthStack } from './auth-stack';
import { IntegrationTestRoleStack } from './integration-test-role-stack';
import { StackNames } from './utils/stack-names';

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

    // Auth Stack
    const authStack = new AuthStack(this, 'Auth', {
      environment: props.stage,
    });

    // Odds collector Lambda stack
    new OddsCollectorStack(this, 'OddsCollector', {
      environment: props.stage,
      betsTableName: `carpool-bets-v2-${props.stage}`,
    });

    // Bet collector API stack
    const betCollectorApiStack = new BetCollectorApiStack(this, 'BetCollectorApi', {
      environment: props.stage,
      betsTableName: `carpool-bets-v2-${props.stage}`,
      userPool: authStack.userPool,
    });

    // Add explicit dependency to ensure DynamoDB deploys before BetCollectorApi
    betCollectorApiStack.addDependency(dynamoStack);

    // Prediction generator stack
    new PredictionGeneratorStack(this, 'PredictionGenerator', {
      environment: props.stage,
      betsTable: dynamoStack.betsTable,
    });

    // Recommendation generator stack
    new RecommendationGeneratorStack(this, 'RecommendationGenerator', {
      environment: props.stage,
      dynamoDbTableName: `carpool-bets-v2-${props.stage}`,
      dynamoDbTableArn: dynamoStack.betsTable.tableArn,
    });

    // Outcome collector stack
    new OutcomeCollectorStack(this, 'OutcomeCollector', {
      environment: props.stage,
      dynamoDbTableName: `carpool-bets-v2-${props.stage}`,
      dynamoDbTableArn: dynamoStack.betsTable.tableArn,
      oddsApiSecretArn: `arn:aws:secretsmanager:us-east-1:${this.account}:secret:odds-api-key-${props.stage}-abc123`,
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
