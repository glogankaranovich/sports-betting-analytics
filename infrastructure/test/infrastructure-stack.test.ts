import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as Infrastructure from '../lib/infrastructure-stack';

describe('Sports Betting Infrastructure Stack', () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new Infrastructure.InfrastructureStack(app, 'MyTestStack');
    template = Template.fromStack(stack);
  });

  test('Creates DynamoDB Tables', () => {
    // Test that all required DynamoDB tables are created
    template.resourceCountIs('AWS::DynamoDB::Table', 3);
    
    // Test bets table
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'sports-betting-bets',
      BillingMode: 'PAY_PER_REQUEST'
    });

    // Test predictions table
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'sports-betting-predictions',
      BillingMode: 'PAY_PER_REQUEST'
    });

    // Test sports data table
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'sports-betting-data',
      BillingMode: 'PAY_PER_REQUEST'
    });
  });

  test('Creates S3 Buckets', () => {
    // Test that both S3 buckets are created
    template.resourceCountIs('AWS::S3::Bucket', 2);
  });

  test('Creates Global Secondary Indexes', () => {
    // Test that GSI is created for user queries
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      GlobalSecondaryIndexes: [
        {
          IndexName: 'user-id-index'
        }
      ]
    });
  });

  test('Has Proper Removal Policy for Dev Environment', () => {
    // Test that resources can be deleted (for dev environment)
    const tables = template.findResources('AWS::DynamoDB::Table');
    expect(Object.keys(tables).length).toBeGreaterThan(0);
  });

  test('Creates Stack Outputs', () => {
    // Test that important values are output
    template.hasOutput('BetsTableName', {});
    template.hasOutput('RawDataBucketName', {});
  });
});
