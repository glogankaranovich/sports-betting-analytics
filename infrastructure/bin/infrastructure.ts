#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { DynamoDBStack } from '../lib/dynamodb-stack';
import { CarpoolBetsPipelineStack } from '../lib/pipeline-stack';
import { ENVIRONMENTS } from '../lib/config/environments';

const app = new cdk.App();

// Check if we're deploying the pipeline or individual stacks
const deployPipeline = app.node.tryGetContext('pipeline') === 'true';

if (deployPipeline) {
  // Deploy pipeline stack (runs in pipeline account)
  new CarpoolBetsPipelineStack(app, 'CarpoolBetsPipelineStack', {
    env: {
      account: '083314012659', // Pipeline account
      region: 'us-east-1',
    },
  });
} else {
  // Manual deployment for dev environment
  const environment = app.node.tryGetContext('environment') || 'dev';
  
  new DynamoDBStack(app, `CarpoolBetsDynamoDBStack-${environment}`, {
    environment: environment,
    env: ENVIRONMENTS[environment as keyof typeof ENVIRONMENTS],
  });
}
