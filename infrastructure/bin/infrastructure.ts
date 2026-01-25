#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { DynamoDBStack } from '../lib/dynamodb-stack';
import { OddsCollectorStack } from '../lib/odds-collector-stack';
import { BetCollectorApiStack } from '../lib/bet-collector-api-stack';
import { OutcomeCollectorStack } from '../lib/outcome-collector-stack';
import { PlayerStatsCollectorStack } from '../lib/player-stats-collector-stack';
import { TeamStatsCollectorStack } from '../lib/team-stats-collector-stack';
import { ModelAnalyticsStack } from '../lib/model-analytics-stack';
import { AnalysisGeneratorStack } from '../lib/analysis-generator-stack';
import { InsightGeneratorStack } from '../lib/insight-generator-stack';
import { MonitoringStack } from '../lib/monitoring-stack';
import { AuthStack } from '../lib/auth-stack';
import { AmplifyStack } from '../lib/amplify-stack';
import { ComplianceStack } from '../lib/compliance-stack';
import { CarpoolBetsPipelineStack } from '../lib/pipeline-stack';
import { SeasonManagerStack } from '../lib/season-manager-stack';
import { ScheduleCollectorStack } from '../lib/schedule-collector-stack';
import { InjuryCollectorStack } from '../lib/injury-collector-stack';
import { StackNames } from '../lib/utils/stack-names';
import { ENVIRONMENTS } from '../lib/config/environments';

const app = new cdk.App();

// Simple logic: if environment=dev, deploy dev stacks, otherwise deploy pipeline
const environment = app.node.tryGetContext('environment');

if (environment === 'dev') {
  // Manual dev deployment - deploy DynamoDB, auth, odds collector, API, and prediction generator
  const dynamoStack = new DynamoDBStack(app, StackNames.forEnvironment('dev', 'DynamoDB'), {
    environment: 'dev',
    env: ENVIRONMENTS.dev,
  });

  const authStack = new AuthStack(app, StackNames.forEnvironment('dev', 'Auth'), {
    environment: 'dev',
    env: ENVIRONMENTS.dev,
  });
  
  const oddsCollectorStack = new OddsCollectorStack(app, StackNames.forEnvironment('dev', 'OddsCollector'), {
    environment: 'dev',
    betsTableName: 'carpool-bets-v2-dev',
    env: ENVIRONMENTS.dev,
  });

  new BetCollectorApiStack(app, StackNames.forEnvironment('dev', 'BetCollectorApi'), {
    environment: 'dev',
    betsTableName: 'carpool-bets-v2-dev',
    userPool: authStack.userPool,
    env: ENVIRONMENTS.dev,
  });

  const outcomeCollectorStack = new OutcomeCollectorStack(app, StackNames.forEnvironment('dev', 'OutcomeCollector'), {
    environment: 'dev',
    dynamoDbTableName: 'carpool-bets-v2-dev',
    dynamoDbTableArn: dynamoStack.betsTable.tableArn,
    env: ENVIRONMENTS.dev,
  });

  const playerStatsCollectorStack = new PlayerStatsCollectorStack(app, StackNames.forEnvironment('dev', 'PlayerStatsCollector'), {
    environment: 'dev',
    betsTableName: 'carpool-bets-v2-dev',
    env: ENVIRONMENTS.dev,
  });

  const teamStatsCollectorStack = new TeamStatsCollectorStack(app, StackNames.forEnvironment('dev', 'TeamStatsCollector'), {
    environment: 'dev',
    table: dynamoStack.betsTable,
    env: ENVIRONMENTS.dev,
  });

  const modelAnalyticsStack = new ModelAnalyticsStack(app, StackNames.forEnvironment('dev', 'ModelAnalytics'), {
    betsTable: dynamoStack.betsTable,
    env: ENVIRONMENTS.dev,
  });

  const analysisGeneratorStack = new AnalysisGeneratorStack(app, StackNames.forEnvironment('dev', 'AnalysisGenerator'), {
    environment: 'dev',
    betsTableName: 'carpool-bets-v2-dev',
    env: ENVIRONMENTS.dev,
  });

  const insightGeneratorStack = new InsightGeneratorStack(app, StackNames.forEnvironment('dev', 'InsightGenerator'), {
    environment: 'dev',
    betsTable: dynamoStack.betsTable,
    env: ENVIRONMENTS.dev,
  });

  const seasonManagerStack = new SeasonManagerStack(app, StackNames.forEnvironment('dev', 'SeasonManager'), {
    environment: 'dev',
    env: ENVIRONMENTS.dev,
  });

  const scheduleCollectorStack = new ScheduleCollectorStack(app, StackNames.forEnvironment('dev', 'ScheduleCollector'), {
    environment: 'dev',
    betsTableName: 'carpool-bets-v2-dev',
    env: ENVIRONMENTS.dev,
  });

  const injuryCollectorStack = new InjuryCollectorStack(app, StackNames.forEnvironment('dev', 'InjuryCollector'), {
    environment: 'dev',
    betsTableName: 'carpool-bets-v2-dev',
    env: ENVIRONMENTS.dev,
  });

  const complianceStack = new ComplianceStack(app, StackNames.forEnvironment('dev', 'Compliance'), {
    env: ENVIRONMENTS.dev,
  });

  new MonitoringStack(app, StackNames.forEnvironment('dev', 'Monitoring'), {
    environment: 'dev',
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
    insightGeneratorFunctions: [
      insightGeneratorStack.insightGeneratorNBA,
      insightGeneratorStack.insightGeneratorNFL,
      insightGeneratorStack.insightGeneratorMLB,
      insightGeneratorStack.insightGeneratorNHL,
      insightGeneratorStack.insightGeneratorEPL
    ],
    playerStatsCollectorFunction: playerStatsCollectorStack.playerStatsCollectorFunction,
    teamStatsCollectorFunction: teamStatsCollectorStack.teamStatsCollectorFunction,
    injuryCollectorFunction: injuryCollectorStack.injuryCollectorFunction,
    outcomeCollectorFunction: outcomeCollectorStack.outcomeCollectorFunction,
    modelAnalyticsFunction: modelAnalyticsStack.modelAnalyticsFunction,
    seasonManagerFunction: seasonManagerStack.seasonManagerFunction,
    complianceLoggerFunction: complianceStack.complianceLoggerFunction,
    env: ENVIRONMENTS.dev,
  });
} else {
  // Deploy pipeline stack and Amplify in pipeline account
  new CarpoolBetsPipelineStack(app, 'CarpoolBetsPipelineStack', {
    env: {
      account: '083314012659', // Pipeline account
      region: 'us-east-1',
    },
  });

  // Deploy Amplify for frontend hosting (handles all branches)
  new AmplifyStack(app, 'CarpoolBetsAmplifyStack', {
    env: {
      account: '083314012659', // Pipeline account
      region: 'us-east-1',
    },
  });
}
