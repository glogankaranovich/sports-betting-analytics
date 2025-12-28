import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface InfrastructureStackProps extends cdk.StackProps {
  stage: string;
}

export class InfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: InfrastructureStackProps) {
    super(scope, id, props);

    // DynamoDB Tables
    const betsTable = new dynamodb.Table(this, 'BetsTable', {
      tableName: `sports-betting-bets-${props.stage}`,
      partitionKey: { name: 'bet_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // Add GSI for user queries
    betsTable.addGlobalSecondaryIndex({
      indexName: 'user-id-index',
      partitionKey: { name: 'user_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
    });

    const predictionsTable = new dynamodb.Table(this, 'PredictionsTable', {
      tableName: `sports-betting-predictions-${props.stage}`,
      partitionKey: { name: 'prediction_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'created_at', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    const sportsDataTable = new dynamodb.Table(this, 'SportsDataTable', {
      tableName: `sports-betting-data-${props.stage}`,
      partitionKey: { name: 'data_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'collected_at', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // S3 Buckets
    const rawDataBucket = new s3.Bucket(this, 'RawDataBucket', {
      bucketName: `sports-betting-raw-data-${props.stage}-${cdk.Aws.ACCOUNT_ID}`,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.stage !== 'prod',
    });

    const assetsBucket = new s3.Bucket(this, 'AssetsBucket', {
      bucketName: `sports-betting-assets-${props.stage}-${cdk.Aws.ACCOUNT_ID}`,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.stage !== 'prod',
    });

    // Output important values
    new cdk.CfnOutput(this, 'BetsTableName', {
      value: betsTable.tableName,
    });

    new cdk.CfnOutput(this, 'RawDataBucketName', {
      value: rawDataBucket.bucketName,
    });
  }
}
