#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { DynamoDBStack } from '../lib/dynamodb-stack';
import { OddsCollectorStack } from '../lib/odds-collector-stack';
import { BetCollectorApiStack } from '../lib/bet-collector-api-stack';
import { PredictionGeneratorStack } from '../lib/prediction-generator-stack';
import { AuthStack } from '../lib/auth-stack';
import { AmplifyStack } from '../lib/amplify-stack';
import { CarpoolBetsPipelineStack } from '../lib/pipeline-stack';
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
  
  new OddsCollectorStack(app, StackNames.forEnvironment('dev', 'OddsCollector'), {
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

  new PredictionGeneratorStack(app, StackNames.forEnvironment('dev', 'PredictionGenerator'), {
    environment: 'dev',
    betsTable: dynamoStack.betsTable,
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
