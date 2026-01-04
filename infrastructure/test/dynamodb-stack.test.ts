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
      TableName: 'carpool-bets-v2-test',
      BillingMode: 'PAY_PER_REQUEST',
      KeySchema: [
        {
          AttributeName: 'pk',
          KeyType: 'HASH'
        },
        {
          AttributeName: 'sk',
          KeyType: 'RANGE'
        }
      ],
      AttributeDefinitions: [
        {
          AttributeName: 'pk',
          AttributeType: 'S'
        },
        {
          AttributeName: 'sk',
          AttributeType: 'S'
        },
        {
          AttributeName: 'active_prediction_pk',
          AttributeType: 'S'
        },
        {
          AttributeName: 'commence_time',
          AttributeType: 'S'
        },
        {
          AttributeName: 'active_bet_pk',
          AttributeType: 'S'
        }
      ],
      GlobalSecondaryIndexes: [
        {
          IndexName: 'ActivePredictionsIndexV2',
          KeySchema: [
            {
              AttributeName: 'active_prediction_pk',
              KeyType: 'HASH'
            },
            {
              AttributeName: 'commence_time',
              KeyType: 'RANGE'
            }
          ],
          Projection: {
            ProjectionType: 'ALL'
          }
        },
        {
          IndexName: 'ActiveBetsIndexV2',
          KeySchema: [
            {
              AttributeName: 'active_bet_pk',
              KeyType: 'HASH'
            },
            {
              AttributeName: 'commence_time',
              KeyType: 'RANGE'
            }
          ],
          Projection: {
            ProjectionType: 'ALL'
          }
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
