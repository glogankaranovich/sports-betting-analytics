#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib/core';
import { SportsBettingStage } from '../lib/sports-betting-stage';
import { ENVIRONMENTS } from '../src/config/environments';

const app = new cdk.App();

// Create standalone dev stage for manual deployment
new SportsBettingStage(app, 'dev', {
  env: ENVIRONMENTS.dev,
  stage: 'dev',
});
