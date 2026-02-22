import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { DynamoDBStack } from './dynamodb-stack';
import { OddsCollectorStack } from './odds-collector-stack';
import { BetCollectorApiStack } from './bet-collector-api-stack';
import { OutcomeCollectorStack } from './outcome-collector-stack';
import { PlayerStatsCollectorStack } from './player-stats-collector-stack';
import { TeamStatsCollectorStack } from './team-stats-collector-stack';
import { SeasonStatsCollectorStack } from './season-stats-collector-stack';
import { ModelAnalyticsStack } from './model-analytics-stack';
import { AuthStack } from './auth-stack';
import { ComplianceStack } from './compliance-stack';
import { IntegrationTestRoleStack } from './integration-test-role-stack';
import { AnalysisGeneratorStack } from './analysis-generator-stack';
import { OddsCollectorScheduleStack } from './odds-collector-schedule-stack';
import { AnalysisGeneratorScheduleStack } from './analysis-generator-schedule-stack';
import { ModelAnalyticsScheduleStack } from './model-analytics-schedule-stack';
import { MonitoringStack } from './monitoring-stack';
import { SeasonManagerStack } from './season-manager-stack';
import { ScheduleCollectorStack } from './schedule-collector-stack';
import { InjuryCollectorStack } from './injury-collector-stack';
import { UserModelsStack } from './user-models-stack';
import { AIAgentStack } from './ai-agent-stack';
import { BennyTraderStack } from './benny-trader-stack';
import { BennyTraderScheduleStack } from './benny-trader-schedule-stack';
import { ModelComparisonCacheStack } from './model-comparison-cache-stack';
import { CustomDataStack } from './custom-data-stack';
import { NewsCollectorsStack } from './news-collectors-stack';
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

    // Model analytics stack
    const modelAnalyticsStack = new ModelAnalyticsStack(this, 'ModelAnalytics', {
      betsTable: dynamoStack.betsTable,
    });

    // User models stack
    const userModelsStack = new UserModelsStack(this, 'UserModels', {
      betsTableName: `carpool-bets-v2-${props.stage}`,
    });

    // Custom data stack
    const customDataStack = new CustomDataStack(this, 'CustomData', {
      environment: props.stage,
    });

    // Bet collector API stack
    const betCollectorApiStack = new BetCollectorApiStack(this, 'BetCollectorApi', {
      environment: props.stage,
      betsTableName: `carpool-bets-v2-${props.stage}`,
      userModelsTableName: userModelsStack.userModelsTable.tableName,
      modelPredictionsTableName: userModelsStack.modelPredictionsTable.tableName,
      customDataTableName: customDataStack.customDataTable.tableName,
      customDataBucketName: customDataStack.customDataBucket.bucketName,
      customDataTable: customDataStack.customDataTable,
      customDataBucket: customDataStack.customDataBucket,
      userPool: authStack.userPool,
      modelAnalyticsFunction: modelAnalyticsStack.modelAnalyticsFunction,
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

    // Season stats collector stack (ESPN statistics API)
    const seasonStatsCollectorStack = new SeasonStatsCollectorStack(this, 'SeasonStatsCollector', {
      environment: props.stage,
      table: dynamoStack.betsTable,
    });

    // Analysis generator stack
    const analysisGeneratorStack = new AnalysisGeneratorStack(this, 'AnalysisGenerator', {
      environment: props.stage,
      betsTableName: `carpool-bets-v2-${props.stage}`,
    });

    // Season manager stack
    const seasonManagerStack = new SeasonManagerStack(this, 'SeasonManager', {
      environment: props.stage,
    });

    // Schedule collector stack
    const scheduleCollectorStack = new ScheduleCollectorStack(this, 'ScheduleCollector', {
      environment: props.stage,
      betsTableName: `carpool-bets-v2-${props.stage}`,
    });

    // Injury collector stack
    const injuryCollectorStack = new InjuryCollectorStack(this, 'InjuryCollector', {
      environment: props.stage,
      betsTableName: `carpool-bets-v2-${props.stage}`,
    });

    // Compliance stack
    const complianceStack = new ComplianceStack(this, 'Compliance', {});

    // AI Agent stack
    new AIAgentStack(this, 'AIAgent', {
      stage: props.stage,
      dynamodbTableName: `carpool-bets-v2-${props.stage}`,
    });

    // Benny trader stack
    const bennyTraderStack = new BennyTraderStack(this, 'BennyTrader', {
      betsTable: dynamoStack.betsTable,
    });

    // Benny trader schedule
    new BennyTraderScheduleStack(this, 'BennyTraderSchedule', {
      bennyTraderFunction: bennyTraderStack.bennyTraderFunction,
    });

    // Schedule stacks - simplified to avoid Lambda permission limit
    new OddsCollectorScheduleStack(this, 'OddsSchedule', {
      environment: props.stage,
      oddsCollectorFunction: oddsCollectorStack.oddsCollectorFunction,
      propsCollectorFunction: oddsCollectorStack.propsCollectorFunction,
    });

    new AnalysisGeneratorScheduleStack(this, 'AnalysisSchedule', {
      environment: props.stage,
      analysisGeneratorNBA: analysisGeneratorStack.analysisGeneratorNBA,
      analysisGeneratorNFL: analysisGeneratorStack.analysisGeneratorNFL,
      analysisGeneratorMLB: analysisGeneratorStack.analysisGeneratorMLB,
      analysisGeneratorNHL: analysisGeneratorStack.analysisGeneratorNHL,
      analysisGeneratorEPL: analysisGeneratorStack.analysisGeneratorEPL,
    });

    // News Collectors Stack (ESPN)
    new NewsCollectorsStack(this, 'NewsCollectors', {
      environment: props.stage,
      betsTable: dynamoStack.betsTable,
    });

    // Monitoring stack
    new MonitoringStack(this, 'Monitoring', {
      environment: props.stage,
      oddsCollectorFunction: oddsCollectorStack.oddsCollectorFunction,
      propsCollectorFunction: oddsCollectorStack.propsCollectorFunction,
      scheduleCollectorFunction: scheduleCollectorStack.scheduleCollectorFunction,
      analysisGeneratorFunctions: [
        analysisGeneratorStack.analysisGeneratorNBA,
        analysisGeneratorStack.analysisGeneratorNFL,
        analysisGeneratorStack.analysisGeneratorMLB,
        analysisGeneratorStack.analysisGeneratorNHL,
        analysisGeneratorStack.analysisGeneratorEPL
      ],
      playerStatsCollectorFunction: playerStatsCollectorStack.playerStatsCollectorFunction,
      teamStatsCollectorFunction: teamStatsCollectorStack.teamStatsCollectorFunction,
      seasonStatsCollectorFunction: seasonStatsCollectorStack.seasonStatsCollectorFunction,
      injuryCollectorFunction: injuryCollectorStack.injuryCollectorFunction,
      outcomeCollectorFunction: outcomeCollectorStack.outcomeCollectorFunction,
      modelAnalyticsFunction: modelAnalyticsStack.modelAnalyticsFunction,
      seasonManagerFunction: seasonManagerStack.seasonManagerFunction,
      complianceLoggerFunction: complianceStack.complianceLoggerFunction,
      bennyTraderFunction: bennyTraderStack.bennyTraderFunction,
      betCollectorApiFunction: betCollectorApiStack.betCollectorApiFunction,
      userModelsApiFunction: betCollectorApiStack.userModelsApiFunction,
      aiAgentApiFunction: betCollectorApiStack.aiAgentApiFunction,
      modelExecutorFunction: userModelsStack.modelExecutorFunction,
      queueLoaderFunction: userModelsStack.queueLoaderFunction,
    });

    new ModelAnalyticsScheduleStack(this, 'ModelAnalyticsSchedule', {
      modelAnalyticsFunction: modelAnalyticsStack.modelAnalyticsFunction,
    });

    // Model Comparison Cache Stack
    new ModelComparisonCacheStack(this, 'ModelComparisonCache', {
      environment: props.stage,
      tableName: `carpool-bets-v2-${props.stage}`,
      tableArn: dynamoStack.betsTable.tableArn,
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
