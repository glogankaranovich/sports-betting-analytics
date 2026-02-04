import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as lambdaEventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class UserModelsStack extends cdk.Stack {
  public readonly userModelsTable: dynamodb.Table;
  public readonly modelPredictionsTable: dynamodb.Table;
  public readonly modelExecutionQueue: sqs.Queue;
  public readonly modelExecutorFunction: lambda.Function;
  public readonly queueLoaderFunction: lambda.Function;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // User Models Table
    this.userModelsTable = new dynamodb.Table(this, 'UserModelsTable', {
      tableName: `${id}-UserModels`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
    });

    // GSI for listing user's models by creation date
    this.userModelsTable.addGlobalSecondaryIndex({
      indexName: 'UserModelsIndex',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Model Predictions Table
    this.modelPredictionsTable = new dynamodb.Table(this, 'ModelPredictionsTable', {
      tableName: `${id}-ModelPredictions`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
    });

    // GSI for querying predictions by outcome
    this.modelPredictionsTable.addGlobalSecondaryIndex({
      indexName: 'ModelPerformanceIndex',
      partitionKey: { name: 'GSI1PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'GSI1SK', type: dynamodb.AttributeType.STRING },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Dead Letter Queue for failed model executions
    const dlq = new sqs.Queue(this, 'ModelExecutionDLQ', {
      queueName: `${id}-ModelExecutionDLQ`,
      retentionPeriod: cdk.Duration.days(14),
    });

    // SQS Queue for model execution
    this.modelExecutionQueue = new sqs.Queue(this, 'ModelExecutionQueue', {
      queueName: `${id}-ModelExecutionQueue`,
      visibilityTimeout: cdk.Duration.seconds(300), // 5 minutes
      receiveMessageWaitTime: cdk.Duration.seconds(20), // Long polling
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: 3, // Retry 3 times before DLQ
      },
    });

    // Model Executor Lambda (processes messages from queue)
    this.modelExecutorFunction = new lambda.Function(this, 'ModelExecutorFunction', {
      functionName: `${id}-ModelExecutor`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'user_model_executor.handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      environment: {
        USER_MODELS_TABLE: this.userModelsTable.tableName,
        MODEL_PREDICTIONS_TABLE: this.modelPredictionsTable.tableName,
        BETS_TABLE: 'carpool-bets-v2-dev', // TODO: Pass from props
      },
    });

    // Grant permissions to executor
    this.userModelsTable.grantReadData(this.modelExecutorFunction);
    this.modelPredictionsTable.grantWriteData(this.modelExecutorFunction);
    
    // Grant read access to bets table and its GSIs
    const betsTable = dynamodb.Table.fromTableName(this, 'BetsTable', 'carpool-bets-v2-dev');
    betsTable.grantReadData(this.modelExecutorFunction);
    
    // Explicitly grant access to GSI
    this.modelExecutorFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['dynamodb:Query'],
      resources: [
        `arn:aws:dynamodb:${cdk.Stack.of(this).region}:${cdk.Stack.of(this).account}:table/carpool-bets-v2-dev/index/*`
      ],
    }));

    // Connect SQS to Lambda (batch size 10)
    this.modelExecutorFunction.addEventSource(
      new lambdaEventSources.SqsEventSource(this.modelExecutionQueue, {
        batchSize: 10,
        maxBatchingWindow: cdk.Duration.seconds(5),
        reportBatchItemFailures: true, // Partial batch failures
      })
    );

    // Queue Loader Lambda (runs on schedule)
    this.queueLoaderFunction = new lambda.Function(this, 'QueueLoaderFunction', {
      functionName: `${id}-QueueLoader`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'user_model_queue_loader.handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.seconds(60),
      memorySize: 256,
      environment: {
        USER_MODELS_TABLE: this.userModelsTable.tableName,
        MODEL_EXECUTION_QUEUE_URL: this.modelExecutionQueue.queueUrl,
      },
    });

    // Grant permissions to queue loader
    this.userModelsTable.grantReadData(this.queueLoaderFunction);
    this.modelExecutionQueue.grantSendMessages(this.queueLoaderFunction);

    // Schedule queue loader to run every 4 hours (same as system models)
    const rule = new events.Rule(this, 'QueueLoaderSchedule', {
      schedule: events.Schedule.rate(cdk.Duration.hours(4)),
      description: 'Load user models into execution queue every 4 hours',
    });

    rule.addTarget(new targets.LambdaFunction(this.queueLoaderFunction));

    // Outputs
    new cdk.CfnOutput(this, 'UserModelsTableName', {
      value: this.userModelsTable.tableName,
      description: 'User Models DynamoDB Table Name',
    });

    new cdk.CfnOutput(this, 'ModelPredictionsTableName', {
      value: this.modelPredictionsTable.tableName,
      description: 'Model Predictions DynamoDB Table Name',
    });

    new cdk.CfnOutput(this, 'ModelExecutionQueueUrl', {
      value: this.modelExecutionQueue.queueUrl,
      description: 'Model Execution SQS Queue URL',
    });
  }
}
