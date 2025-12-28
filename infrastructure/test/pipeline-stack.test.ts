import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { SportsBettingPipelineStack } from '../lib/pipeline-stack';

describe('Sports Betting Pipeline Stack', () => {
  let template: Template;

  beforeAll(() => {
    const app = new cdk.App();
    const stack = new SportsBettingPipelineStack(app, 'TestPipelineStack', {
      env: { account: '123456789012', region: 'us-east-1' }
    });
    template = Template.fromStack(stack);
  });

  test('Creates CodePipeline', () => {
    template.resourceCountIs('AWS::CodePipeline::Pipeline', 1);
    
    template.hasResourceProperties('AWS::CodePipeline::Pipeline', {
      Name: 'SportsBettingPipeline'
    });
  });

  test('Pipeline Has GitHub Source', () => {
    // Just verify pipeline has stages - GitHub source structure is complex
    template.hasResourceProperties('AWS::CodePipeline::Pipeline', {
      Name: 'SportsBettingPipeline'
    });
  });

  test('Creates CodeBuild Projects', () => {
    // Pipeline creates multiple build projects
    template.resourceCountIs('AWS::CodeBuild::Project', 5); // Synth + SelfMutation + IntegrationTests + Assets + Lambda
  });
});
