#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { DynamoDBStack } from '../lib/dynamodb-stack';
import { OddsCollectorStack } from '../lib/odds-collector-stack';
import { CarpoolBetsPipelineStack } from '../lib/pipeline-stack';
import { ENVIRONMENTS } from '../lib/config/environments';

const app = new cdk.App();

// Simple logic: if environment=dev, deploy dev stacks, otherwise deploy pipeline
const environment = app.node.tryGetContext('environment');

if (environment === 'dev') {
  // Manual dev deployment - deploy both DynamoDB and odds collector
  new DynamoDBStack(app, 'CarpoolBetsDynamoDBStack-dev', {
    environment: 'dev',
    env: ENVIRONMENTS.dev,
  });
  
  new OddsCollectorStack(app, 'CarpoolBetsOddsCollectorStack-dev', {
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
