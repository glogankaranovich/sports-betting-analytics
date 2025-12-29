import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as Infrastructure from '../lib/infrastructure-stack';

describe('Sports Betting Infrastructure Stack', () => {
  test('Creates DynamoDB Tables with Stage Names', () => {
    const devApp = new cdk.App();
    const devStack = new Infrastructure.InfrastructureStack(devApp, 'DevTestStack', {
      stage: 'dev'
    });
    const devTemplate = Template.fromStack(devStack);

    devTemplate.resourceCountIs('AWS::DynamoDB::Table', 5);
    devTemplate.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'sports-betting-bets-dev',
      BillingMode: 'PAY_PER_REQUEST'
    });
  });

  test('Creates S3 Buckets with Stage Names', () => {
    const app = new cdk.App();
    const stack = new Infrastructure.InfrastructureStack(app, 'TestStack', {
      stage: 'dev'
    });
    const template = Template.fromStack(stack);

    template.resourceCountIs('AWS::S3::Bucket', 3);
  });

  test('Has Different Removal Policies by Stage', () => {
    const devApp = new cdk.App();
    const devStack = new Infrastructure.InfrastructureStack(devApp, 'DevStack', {
      stage: 'dev'
    });
    const devTemplate = Template.fromStack(devStack);

    const prodApp = new cdk.App();
    const prodStack = new Infrastructure.InfrastructureStack(prodApp, 'ProdStack', {
      stage: 'prod'
    });
    const prodTemplate = Template.fromStack(prodStack);

    // Dev should have Delete policy
    const devTables = devTemplate.findResources('AWS::DynamoDB::Table');
    expect(Object.values(devTables)[0].DeletionPolicy).toBe('Delete');

    // Prod should have Retain policy  
    const prodTables = prodTemplate.findResources('AWS::DynamoDB::Table');
    expect(Object.values(prodTables)[0].DeletionPolicy).toBe('Retain');
  });

  test('Creates Global Secondary Indexes', () => {
    const app = new cdk.App();
    const stack = new Infrastructure.InfrastructureStack(app, 'TestStack', {
      stage: 'dev'
    });
    const template = Template.fromStack(stack);

    template.hasResourceProperties('AWS::DynamoDB::Table', {
      GlobalSecondaryIndexes: [
        {
          IndexName: 'user-id-index'
        }
      ]
    });
  });

  test('Creates Stack Outputs', () => {
    const app = new cdk.App();
    const stack = new Infrastructure.InfrastructureStack(app, 'TestStack', {
      stage: 'dev'
    });
    const template = Template.fromStack(stack);

    template.hasOutput('BetsTableName', {});
    template.hasOutput('RawDataBucketName', {});
  });
});
