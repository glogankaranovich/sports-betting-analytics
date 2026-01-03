import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface DynamoDBStackProps extends cdk.StackProps {
  environment: string;
}

export class DynamoDBStack extends cdk.Stack {
  public readonly betsTable: dynamodb.Table;
  public readonly betsTableName: cdk.CfnOutput;

  constructor(scope: Construct, id: string, props: DynamoDBStackProps) {
    super(scope, id, props);

    // Table for storing betting odds data and predictions
    this.betsTable = new dynamodb.Table(this, 'BetsTable', {
      tableName: `carpool-bets-v2-${props.environment}`,
      partitionKey: { 
        name: 'pk', 
        type: dynamodb.AttributeType.STRING 
      },
      sortKey: { 
        name: 'sk', 
        type: dynamodb.AttributeType.STRING 
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: props.environment === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      timeToLiveAttribute: 'ttl',
    });

    // Add GSI for efficient prediction querying
    this.betsTable.addGlobalSecondaryIndex({
      indexName: 'ActivePredictionsIndex',
      partitionKey: {
        name: 'prediction_type',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'commence_time',
        type: dynamodb.AttributeType.STRING
      }
    });

    // Add GSI for bet type + sport querying (new sparse index)
    this.betsTable.addGlobalSecondaryIndex({
      indexName: 'ActiveBetsIndexV2',
      partitionKey: {
        name: 'active_bet_pk',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'commence_time',
        type: dynamodb.AttributeType.STRING
      }
    });

    // Keep old GSI temporarily for migration
    this.betsTable.addGlobalSecondaryIndex({
      indexName: 'ActiveBetsIndex',
      partitionKey: {
        name: 'bet_type',
        type: dynamodb.AttributeType.STRING
      },
      sortKey: {
        name: 'commence_time',
        type: dynamodb.AttributeType.STRING
      }
    });

    // Output the table name
    this.betsTableName = new cdk.CfnOutput(this, 'BetsTableName', {
      value: this.betsTable.tableName,
      exportName: `BetsTableName-${props.environment}`,
    });
  }
}
