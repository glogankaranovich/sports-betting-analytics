#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { SportsBettingPipelineStack } from '../lib/pipeline-stack';
import { SportsBettingStage } from '../lib/sports-betting-stage';
import { ENVIRONMENTS } from '../lib/config/environments';

const app = new cdk.App();

const stage = app.node.tryGetContext('stages');

if (stage === 'dev') {
  // Create standalone dev stage for manual deployment
  new SportsBettingStage(app, 'dev', {
    env: ENVIRONMENTS.dev,
    stage: 'dev',
  });
} else {
  // Default: Create pipeline (for staging and prod deployments)
  new SportsBettingPipelineStack(app, 'SportsBettingPipelineStack', {
    env: ENVIRONMENTS.pipeline,
  });
}
