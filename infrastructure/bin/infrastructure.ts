#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { DynamoDBStack } from '../lib/dynamodb-stack';
import { OddsCollectorStack } from '../lib/odds-collector-stack';
import { BetCollectorApiStack } from '../lib/bet-collector-api-stack';
import { CarpoolBetsPipelineStack } from '../lib/pipeline-stack';
import { StackNames } from '../lib/utils/stack-names';
import { ENVIRONMENTS } from '../lib/config/environments';

const app = new cdk.App();

// Simple logic: if environment=dev, deploy dev stacks, otherwise deploy pipeline
const environment = app.node.tryGetContext('environment');

if (environment === 'dev') {
  // Manual dev deployment - deploy DynamoDB, odds collector, and API
  new DynamoDBStack(app, StackNames.forEnvironment('dev', 'DynamoDB'), {
    environment: 'dev',
    env: ENVIRONMENTS.dev,
  });
  
  new OddsCollectorStack(app, StackNames.forEnvironment('dev', 'OddsCollector'), {
    environment: 'dev',
    betsTableName: 'carpool-bets-dev',
    env: ENVIRONMENTS.dev,
  });

  new BetCollectorApiStack(app, StackNames.forEnvironment('dev', 'BetCollectorApi'), {
    environment: 'dev',
    betsTableName: 'carpool-bets-dev',
    env: ENVIRONMENTS.dev,
  });
} else {
  // Deploy pipeline stack (for pipeline account and self-mutation)
  new CarpoolBetsPipelineStack(app, 'CarpoolBetsPipelineStack', {
    env: {
      account: '083314012659', // Pipeline account
      region: 'us-east-1',
    },
  });
}
