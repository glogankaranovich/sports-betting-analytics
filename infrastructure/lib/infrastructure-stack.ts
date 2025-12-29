import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface InfrastructureStackProps extends cdk.StackProps {
  stage: string;
}

export class InfrastructureStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: InfrastructureStackProps) {
    super(scope, id, props);

    // Cross-account integration test role
    const integrationTestRole = new iam.Role(this, 'CrossAccountIntegrationTestRole', {
      roleName: `CrossAccountIntegrationTestRole-${props.stage}`,
      assumedBy: new iam.AccountPrincipal('083314012659'), // Pipeline account
      description: 'Role for pipeline account to run integration tests against resources',
    });

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

    // Referee data table for bias tracking
    const refereeDataTable = new dynamodb.Table(this, 'RefereeDataTable', {
      tableName: `sports-betting-referees-${props.stage}`,
      partitionKey: { name: 'referee_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'game_date', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });

    // Model metadata and performance tracking
    const modelsTable = new dynamodb.Table(this, 'ModelsTable', {
      tableName: `sports-betting-models-${props.stage}`,
      partitionKey: { name: 'model_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'version', type: dynamodb.AttributeType.STRING },
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

    // ML models and artifacts bucket
    const modelsBucket = new s3.Bucket(this, 'ModelsBucket', {
      bucketName: `sports-betting-models-${props.stage}-${cdk.Aws.ACCOUNT_ID}`,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: props.stage !== 'prod',
      versioned: true, // Enable versioning for model artifacts
    });

    // Reference existing secret for The Odds API key
    const oddsApiSecret = secretsmanager.Secret.fromSecretNameV2(
      this, 
      'OddsApiSecret', 
      `sports-betting/odds-api-key-${props.stage}`
    );

    // Reference SportsData.io API secret
    const sportsDataSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      'SportsDataSecret',
      'sports-betting/sportsdata-api-key'
    );

    // Lambda function for data collection
    const dataCollectorFunction = new lambda.Function(this, 'DataCollectorFunction', {
      functionName: `sports-betting-data-collector-${props.stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'lambda_handler.lambda_handler',
      code: lambda.Code.fromAsset('../backend/crawler'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        BETS_TABLE_NAME: betsTable.tableName,
        PREDICTIONS_TABLE_NAME: predictionsTable.tableName,
        SPORTS_DATA_TABLE_NAME: sportsDataTable.tableName,
        REFEREE_DATA_TABLE_NAME: refereeDataTable.tableName,
        MODELS_TABLE_NAME: modelsTable.tableName,
        RAW_DATA_BUCKET_NAME: rawDataBucket.bucketName,
        MODELS_BUCKET_NAME: modelsBucket.bucketName,
        STAGE: props.stage,
        ODDS_API_SECRET_ARN: oddsApiSecret.secretArn,
        SPORTSDATA_API_SECRET_ARN: sportsDataSecret.secretArn,
      },
    });

    // Grant permissions to Lambda
    betsTable.grantReadWriteData(dataCollectorFunction);
    predictionsTable.grantReadWriteData(dataCollectorFunction);
    sportsDataTable.grantReadWriteData(dataCollectorFunction);
    refereeDataTable.grantReadWriteData(dataCollectorFunction);
    modelsTable.grantReadWriteData(dataCollectorFunction);
    rawDataBucket.grantReadWrite(dataCollectorFunction);
    modelsBucket.grantReadWrite(dataCollectorFunction);
    oddsApiSecret.grantRead(dataCollectorFunction);
    sportsDataSecret.grantRead(dataCollectorFunction);

    // Grant integration test role read access to resources
    betsTable.grantReadData(integrationTestRole);
    predictionsTable.grantReadData(integrationTestRole);
    sportsDataTable.grantReadData(integrationTestRole);
    refereeDataTable.grantReadData(integrationTestRole);
    modelsTable.grantReadData(integrationTestRole);
    rawDataBucket.grantRead(integrationTestRole);
    modelsBucket.grantRead(integrationTestRole);

    // CloudWatch Events for scheduling
    const sportsCollectionRule = new events.Rule(this, 'SportsCollectionRule', {
      ruleName: `sports-betting-sports-collection-${props.stage}`,
      description: 'Trigger sports data collection every 4 hours',
      schedule: events.Schedule.rate(cdk.Duration.hours(4)),
    });

    const redditCollectionRule = new events.Rule(this, 'RedditCollectionRule', {
      ruleName: `sports-betting-reddit-collection-${props.stage}`,
      description: 'Trigger Reddit insights collection every 2 hours',
      schedule: events.Schedule.rate(cdk.Duration.hours(2)),
    });

    // Add Lambda targets to rules
    sportsCollectionRule.addTarget(new targets.LambdaFunction(dataCollectorFunction, {
      event: events.RuleTargetInput.fromObject({
        collection_type: 'sports',
        source: 'cloudwatch-event'
      })
    }));

    redditCollectionRule.addTarget(new targets.LambdaFunction(dataCollectorFunction, {
      event: events.RuleTargetInput.fromObject({
        collection_type: 'reddit',
        source: 'cloudwatch-event'
      })
    }));

    // API Gateway for manual triggers
    const api = new apigateway.RestApi(this, 'DataCollectionApi', {
      restApiName: `sports-betting-data-api-${props.stage}`,
      description: 'API for manual data collection triggers',
    });

    const dataCollectionIntegration = new apigateway.LambdaIntegration(dataCollectorFunction);

    // POST /collect/sports
    const collectResource = api.root.addResource('collect');
    const sportsResource = collectResource.addResource('sports');
    sportsResource.addMethod('POST', dataCollectionIntegration);

    // POST /collect/reddit  
    const redditResource = collectResource.addResource('reddit');
    redditResource.addMethod('POST', dataCollectionIntegration);

    // Output important values
    new cdk.CfnOutput(this, 'BetsTableName', {
      value: betsTable.tableName,
    });

    new cdk.CfnOutput(this, 'RawDataBucketName', {
      value: rawDataBucket.bucketName,
    });

    new cdk.CfnOutput(this, 'DataCollectorFunctionName', {
      value: dataCollectorFunction.functionName,
    });

    new cdk.CfnOutput(this, 'DataCollectionApiUrl', {
      value: api.url,
    });
  }
}
