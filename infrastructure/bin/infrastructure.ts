#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { DynamoDBStack } from '../lib/dynamodb-stack';
import { CarpoolBetsPipelineStack } from '../lib/pipeline-stack';
import { ENVIRONMENTS } from '../lib/config/environments';

const app = new cdk.App();

// Simple logic: if environment=dev, deploy dev stacks, otherwise deploy pipeline
const environment = app.node.tryGetContext('environment');

if (environment === 'dev') {
  // Manual dev deployment
  new DynamoDBStack(app, 'CarpoolBetsDynamoDBStack-dev', {
    environment: 'dev',
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
