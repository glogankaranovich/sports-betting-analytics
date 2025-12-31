import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { DynamoDBStack } from '../lib/dynamodb-stack';

describe('DynamoDBStack', () => {
  let app: cdk.App;
  let stack: DynamoDBStack;
  let template: Template;

  beforeEach(() => {
    app = new cdk.App();
    stack = new DynamoDBStack(app, 'TestDynamoDBStack', {
      environment: 'test',
    });
    template = Template.fromStack(stack);
  });

  test('creates DynamoDB table with correct properties', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'carpool-bets-test',
      BillingMode: 'PAY_PER_REQUEST',
      KeySchema: [
        {
          AttributeName: 'game_id',
          KeyType: 'HASH'
        },
        {
          AttributeName: 'bookmaker',
          KeyType: 'RANGE'
        }
      ],
      AttributeDefinitions: [
        {
          AttributeName: 'game_id',
          AttributeType: 'S'
        },
        {
          AttributeName: 'bookmaker',
          AttributeType: 'S'
        }
      ]
    });
  });

  test('creates table with correct removal policy for non-prod', () => {
    template.hasResource('AWS::DynamoDB::Table', {
      DeletionPolicy: 'Delete'
    });
  });

  test('creates table with retain policy for prod', () => {
    const prodApp = new cdk.App();
    const prodStack = new DynamoDBStack(prodApp, 'ProdDynamoDBStack', {
      environment: 'prod',
    });
    const prodTemplate = Template.fromStack(prodStack);
    
    prodTemplate.hasResource('AWS::DynamoDB::Table', {
      DeletionPolicy: 'Retain'
    });
  });

  test('exports table name output', () => {
    template.hasOutput('BetsTableName', {
      Export: {
        Name: 'BetsTableName-test'
      }
    });
  });
});
