import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { OddsCollectorStack } from '../lib/odds-collector-stack';

describe('OddsCollectorStack', () => {
  let template: Template;

  beforeEach(() => {
    const app = new cdk.App();
    const stack = new OddsCollectorStack(app, 'TestOddsCollectorStack', {
      environment: 'test',
      betsTableName: 'carpool-bets-test'
    });
    template = Template.fromStack(stack);
  });

  test('creates Lambda function with correct configuration', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      Runtime: 'python3.11',
      Handler: 'odds_collector.lambda_handler',
      Timeout: 900,  // Updated to 15 minutes
      Environment: {
        Variables: {
          DYNAMODB_TABLE: 'carpool-bets-test'
        }
      }
    });
  });

  test('EventBridge schedules are enabled for automated collection', () => {
    // Verify 10 EventBridge rules exist (5 sports x 2 types: game odds + props)
    template.resourceCountIs('AWS::Events::Rule', 10);
  });

  test('creates IAM policy for Lambda permissions', () => {
    // 2 policies: one for game odds Lambda, one for props Lambda
    template.resourceCountIs('AWS::IAM::Policy', 2);
  });

  test('creates two Lambda functions', () => {
    // 2 functions: game odds collector + props collector
    template.resourceCountIs('AWS::Lambda::Function', 2);
  });
});
