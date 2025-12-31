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
      Timeout: 300,
      Environment: {
        Variables: {
          DYNAMODB_TABLE: 'carpool-bets-test'
        }
      }
    });
  });

  test('creates EventBridge rule for scheduling', () => {
    template.hasResourceProperties('AWS::Events::Rule', {
      ScheduleExpression: 'rate(4 hours)'
    });
  });

  test('creates IAM policy for Lambda permissions', () => {
    template.resourceCountIs('AWS::IAM::Policy', 1);
  });

  test('creates exactly one Lambda function', () => {
    template.resourceCountIs('AWS::Lambda::Function', 1);
  });

  test('creates exactly one EventBridge rule', () => {
    template.resourceCountIs('AWS::Events::Rule', 1);
  });
});
