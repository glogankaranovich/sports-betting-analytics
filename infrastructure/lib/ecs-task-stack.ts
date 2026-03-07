#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface EcsTaskStackProps extends cdk.StackProps {
  stage: string;
  cluster: ecs.ICluster;
  tableName: string;
  anthropicApiKeyArn: string;
  oddsApiKeyArn: string;
}

export class EcsTaskStack extends cdk.Stack {
  public readonly propsCollectorTask: ecs.FargateTaskDefinition;
  public readonly analysisGeneratorTask: ecs.FargateTaskDefinition;
  public readonly bennyTraderTask: ecs.FargateTaskDefinition;
  public readonly propsCollectorLogGroup: logs.ILogGroup;
  public readonly analysisGeneratorLogGroup: logs.ILogGroup;
  public readonly bennyTraderLogGroup: logs.ILogGroup;

  constructor(scope: Construct, id: string, props: EcsTaskStackProps) {
    super(scope, id, props);

    // Get ECR repository (create if doesn't exist)
    const repository = new ecr.Repository(this, 'BatchJobsRepo', {
      repositoryName: `${props.stage.toLowerCase()}-batch-jobs`,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          maxImageCount: 10,
          description: 'Keep last 10 images',
        },
      ],
    });

    // Task execution role (for pulling images, writing logs)
    const executionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Allow reading secrets (only if provided)
    if (props.anthropicApiKeyArn) {
      executionRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ['secretsmanager:GetSecretValue'],
          resources: [props.anthropicApiKeyArn, props.oddsApiKeyArn],
        })
      );
    } else {
      executionRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ['secretsmanager:GetSecretValue'],
          resources: [props.oddsApiKeyArn],
        })
      );
    }

    // Task role (for application permissions)
    const taskRole = new iam.Role(this, 'TaskRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
    });

    // Grant DynamoDB access
    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'dynamodb:GetItem',
          'dynamodb:PutItem',
          'dynamodb:UpdateItem',
          'dynamodb:Query',
          'dynamodb:Scan',
          'dynamodb:BatchWriteItem',
        ],
        resources: [
          `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.tableName}`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.tableName}/index/*`,
        ],
      })
    );

    // Grant Bedrock access for AI analysis
    taskRole.addToPolicy(
      new iam.PolicyStatement({
        actions: [
          'bedrock:InvokeModel',
          'bedrock:InvokeModelWithResponseStream',
        ],
        resources: ['*'],
      })
    );

    // Common environment variables
    const commonEnv = {
      ENVIRONMENT: props.stage,
      DYNAMODB_TABLE: props.tableName,
    };

    // Props Collector Task
    this.propsCollectorTask = new ecs.FargateTaskDefinition(this, 'PropsCollectorTask', {
      memoryLimitMiB: 512,
      cpu: 256,
      executionRole,
      taskRole,
    });

    const propsLogGroup = new logs.LogGroup(this, 'PropsCollectorLogGroup', {
      logGroupName: `/ecs/${props.stage}-props-collector`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    this.propsCollectorLogGroup = propsLogGroup;

    this.propsCollectorTask.addContainer('PropsCollector', {
      image: ecs.ContainerImage.fromEcrRepository(repository, 'latest'),
      command: ['python', '-u', 'odds_collector.py'],
      environment: {
        ...commonEnv,
        PROPS_ONLY: 'true',
      },
      secrets: {
        ODDS_API_KEY: ecs.Secret.fromSecretsManager(
          cdk.aws_secretsmanager.Secret.fromSecretCompleteArn(this, 'OddsApiKey', props.oddsApiKeyArn)
        ),
      },
      logging: ecs.LogDrivers.awsLogs({
        logGroup: propsLogGroup,
        streamPrefix: 'props-collector',
      }),
    });

    // Analysis Generator Task
    this.analysisGeneratorTask = new ecs.FargateTaskDefinition(this, 'AnalysisGeneratorTask', {
      memoryLimitMiB: 1024,
      cpu: 512,
      executionRole,
      taskRole,
    });

    const analysisLogGroup = new logs.LogGroup(this, 'AnalysisGeneratorLogGroup', {
      logGroupName: `/ecs/${props.stage}-analysis-generator`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    this.analysisGeneratorLogGroup = analysisLogGroup;

    this.analysisGeneratorTask.addContainer('AnalysisGenerator', {
      image: ecs.ContainerImage.fromEcrRepository(repository, 'latest'),
      command: ['python', '-u', 'analysis_generator.py'],
      environment: {
        ...commonEnv,
        SPORT: 'basketball_nba', // Override via EventBridge
      },
      logging: ecs.LogDrivers.awsLogs({
        logGroup: analysisLogGroup,
        streamPrefix: 'analysis-generator',
      }),
    });

    // Benny Trader Task
    this.bennyTraderTask = new ecs.FargateTaskDefinition(this, 'BennyTraderTask', {
      memoryLimitMiB: 1024,
      cpu: 512,
      executionRole,
      taskRole,
    });

    const bennyLogGroup = new logs.LogGroup(this, 'BennyTraderLogGroup', {
      logGroupName: `/ecs/${props.stage}-benny-trader`,
      retention: logs.RetentionDays.ONE_WEEK,
      removalPolicy: cdk.RemovalPolicy.DESTROY,
    });
    this.bennyTraderLogGroup = bennyLogGroup;

    this.bennyTraderTask.addContainer('BennyTrader', {
      image: ecs.ContainerImage.fromEcrRepository(repository, 'latest'),
      command: ['python', '-u', 'benny_trader.py'],
      environment: commonEnv,
      logging: ecs.LogDrivers.awsLogs({
        logGroup: bennyLogGroup,
        streamPrefix: 'benny-trader',
      }),
    });

    // Outputs
    new cdk.CfnOutput(this, 'RepositoryUri', {
      value: repository.repositoryUri,
      exportName: `${props.stage}-BatchJobsRepoUri`,
    });

    new cdk.CfnOutput(this, 'PropsCollectorTaskArn', {
      value: this.propsCollectorTask.taskDefinitionArn,
    });

    new cdk.CfnOutput(this, 'AnalysisGeneratorTaskArn', {
      value: this.analysisGeneratorTask.taskDefinitionArn,
    });

    new cdk.CfnOutput(this, 'BennyTraderTaskArn', {
      value: this.bennyTraderTask.taskDefinitionArn,
    });
  }
}
