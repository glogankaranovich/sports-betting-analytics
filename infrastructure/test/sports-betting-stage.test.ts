import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { SportsBettingStage } from '../lib/sports-betting-stage';

describe('Sports Betting Stage', () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stage = new SportsBettingStage(app, 'TestStage', {
      stage: 'dev',
      env: { account: '123456789012', region: 'us-east-1' }
    });
    
    // Get the infrastructure stack from the stage
    const infraStack = stage.node.findChild('Infrastructure') as cdk.Stack;
    template = Template.fromStack(infraStack);
  });

  test('Stage Creates Infrastructure Stack', () => {
    // Verify the stage creates the infrastructure stack
    template.resourceCountIs('AWS::DynamoDB::Table', 5);
    template.resourceCountIs('AWS::S3::Bucket', 3);
  });

  test('Stage Passes Correct Props', () => {
    // Verify stage-specific naming
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'sports-betting-bets-dev'
    });
  });
});
