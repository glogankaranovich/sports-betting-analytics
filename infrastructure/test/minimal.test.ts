import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { MinimalStack } from '../lib/minimal-stack';

describe('Minimal Stack Test', () => {
  test('Creates DynamoDB Table', () => {
    const app = new cdk.App();
    const stack = new MinimalStack(app, 'TestStack', {
      stage: 'test'
    });
    const template = Template.fromStack(stack);

    template.resourceCountIs('AWS::DynamoDB::Table', 1);
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'sports-betting-bets-test',
      BillingMode: 'PAY_PER_REQUEST'
    });
  });
});
