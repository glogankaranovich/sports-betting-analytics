import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DynamoDBStack } from './dynamodb-stack';
import { OddsCollectorStack } from './odds-collector-stack';
import { BetCollectorApiStack } from './bet-collector-api-stack';
import { OutcomeCollectorStack } from './outcome-collector-stack';
import { PlayerStatsCollectorStack } from './player-stats-collector-stack';
import { TeamStatsCollectorStack } from './team-stats-collector-stack';
import { ModelAnalyticsStack } from './model-analytics-stack';
import { AuthStack } from './auth-stack';
import { ComplianceStack } from './compliance-stack';
import { IntegrationTestRoleStack } from './integration-test-role-stack';
import { AnalysisGeneratorStack } from './analysis-generator-stack';
import { InsightGeneratorStack } from './insight-generator-stack';
import { MonitoringStack } from './monitoring-stack';
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
    const oddsCollectorStack = new OddsCollectorStack(this, 'OddsCollector', {
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

    // Outcome collector stack
    const outcomeCollectorStack = new OutcomeCollectorStack(this, 'OutcomeCollector', {
      environment: props.stage,
      dynamoDbTableName: `carpool-bets-v2-${props.stage}`,
      dynamoDbTableArn: dynamoStack.betsTable.tableArn,
    });

    // Player stats collector stack
    const playerStatsCollectorStack = new PlayerStatsCollectorStack(this, 'PlayerStatsCollector', {
      environment: props.stage,
      betsTableName: `carpool-bets-v2-${props.stage}`,
    });

    // Team stats collector stack
    const teamStatsCollectorStack = new TeamStatsCollectorStack(this, 'TeamStatsCollector', {
      environment: props.stage,
      table: dynamoStack.betsTable,
    });

    // Analysis generator stack
    const analysisGeneratorStack = new AnalysisGeneratorStack(this, 'AnalysisGenerator', {
      environment: props.stage,
      betsTableName: `carpool-bets-v2-${props.stage}`,
    });

    // Insight generator stack
    const insightGeneratorStack = new InsightGeneratorStack(this, 'InsightGenerator', {
      environment: props.stage,
      betsTable: dynamoStack.betsTable,
    });

    // Model analytics stack
    new ModelAnalyticsStack(this, 'ModelAnalytics', {
      betsTable: dynamoStack.betsTable,
    });

    // Compliance stack
    new ComplianceStack(this, 'Compliance', {});

    // Monitoring stack
    new MonitoringStack(this, 'Monitoring', {
      environment: props.stage,
      oddsCollectorFunction: oddsCollectorStack.oddsCollectorFunction,
      analysisGeneratorFunction: analysisGeneratorStack.analysisGeneratorFunction,
      insightGeneratorFunction: insightGeneratorStack.insightGeneratorFunction,
      playerStatsCollectorFunction: playerStatsCollectorStack.playerStatsCollectorFunction,
      teamStatsCollectorFunction: teamStatsCollectorStack.teamStatsCollectorFunction,
      outcomeCollectorFunction: outcomeCollectorStack.outcomeCollectorFunction,
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
