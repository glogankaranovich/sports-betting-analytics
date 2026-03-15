#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import { Construct } from 'constructs';
import { PLATFORM_CONSTANTS } from './utils/constants';

export interface EcsTaskStackProps extends cdk.StackProps {
  stage: string;
  cluster: ecs.ICluster;
  tableName: string;
  anthropicApiKeyArn?: string;
  oddsApiKeySecretName: string;
  notificationQueueUrl?: string;
  notificationQueueArn?: string;
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

    // Create ECR repository
    const repository = new ecr.Repository(this, 'BatchJobsRepo', {
      repositoryName: `${props.stage}-batch-jobs`,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      lifecycleRules: [
        {
          maxImageCount: 5,
          description: 'Keep last 5 images',
        },
      ],
    });

    // Grant pipeline account permission to push images
    repository.grantPullPush(new iam.AccountPrincipal('083314012659'));

    // Import odds API secret
    const oddsApiSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      'OddsApiSecret',
      props.oddsApiKeySecretName
    );

    // Task execution role (for pulling images, writing logs)
    const executionRole = new iam.Role(this, 'TaskExecutionRole', {
      assumedBy: new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      managedPolicies: [
        iam.ManagedPolicy.fromAwsManagedPolicyName('service-role/AmazonECSTaskExecutionRolePolicy'),
      ],
    });

    // Allow reading secrets
    if (props.anthropicApiKeyArn) {
      executionRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ['secretsmanager:GetSecretValue'],
          resources: [props.anthropicApiKeyArn, oddsApiSecret.secretArn],
        })
      );
    } else {
      executionRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ['secretsmanager:GetSecretValue'],
          resources: [oddsApiSecret.secretArn],
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
          'dynamodb:DeleteItem',
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

    // Grant SQS permissions if notification queue provided
    if (props.notificationQueueArn) {
      taskRole.addToPolicy(
        new iam.PolicyStatement({
          actions: ['sqs:SendMessage'],
          resources: [props.notificationQueueArn],
        })
      );
    }

    // Common environment variables
    const commonEnv = {
      ENVIRONMENT: props.stage,
      DYNAMODB_TABLE: props.tableName,
      IMAGE_VERSION: new Date().toISOString(), // Force new revision
      ...(props.notificationQueueUrl && { NOTIFICATION_QUEUE_URL: props.notificationQueueUrl }),
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
        ODDS_API_KEY: ecs.Secret.fromSecretsManager(oddsApiSecret),
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

    // EventBridge Schedules
    const eventRole = new iam.Role(this, 'EventBridgeEcsRole', {
      assumedBy: new iam.ServicePrincipal('events.amazonaws.com'),
    });

    eventRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['ecs:RunTask'],
        resources: [
          this.propsCollectorTask.taskDefinitionArn,
          this.analysisGeneratorTask.taskDefinitionArn,
          this.bennyTraderTask.taskDefinitionArn,
        ],
      })
    );

    eventRole.addToPolicy(
      new iam.PolicyStatement({
        actions: ['iam:PassRole'],
        resources: [executionRole.roleArn, taskRole.roleArn],
      })
    );

    const subnetSelection: ec2.SubnetSelection = { subnetType: ec2.SubnetType.PUBLIC };

    // Props Collector - every 6 hours
    new events.Rule(this, 'PropsCollectorSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '*/6' }),
      targets: [
        new targets.EcsTask({
          cluster: props.cluster,
          taskDefinition: this.propsCollectorTask,
          role: eventRole,
          subnetSelection,
          assignPublicIp: true,
        }),
      ],
    });

    // Analysis Generators - every 4 hours for each sport, staggered
    const sports = PLATFORM_CONSTANTS.SUPPORTED_SPORTS.split(',');
    const models = PLATFORM_CONSTANTS.SYSTEM_MODELS.split(',').filter(m => m !== 'benny');
    const betTypes = ['games', 'props'];

    let globalOffset = 0;
    sports.forEach((sport) => {
      models.forEach((model) => {
        betTypes.forEach((betType) => {
          const minute = globalOffset % 60;
          const hourOffset = Math.floor(globalOffset / 60);

          new events.Rule(this, `AnalysisGen-${sport}-${model}-${betType}`, {
            schedule: events.Schedule.cron({
              minute: minute.toString(),
              hour: `${hourOffset}/4`,
            }),
            targets: [
              new targets.EcsTask({
                cluster: props.cluster,
                taskDefinition: this.analysisGeneratorTask,
                role: eventRole,
                subnetSelection,
                assignPublicIp: true,
                containerOverrides: [
                  {
                    containerName: 'AnalysisGenerator',
                    environment: [
                      { name: 'SPORT', value: sport },
                      { name: 'MODEL', value: model },
                      { name: 'BET_TYPE', value: betType },
                    ],
                  },
                ],
              }),
            ],
          });

          globalOffset += 2;
        });
      });
    });

    // Benny Trader - multiple times daily
    const bennySchedules = [
      { hour: '13', name: 'Morning' },   // 8 AM ET
      { hour: '17', name: 'Midday' },    // 12 PM ET
      { hour: '21', name: 'Afternoon' }, // 4 PM ET
      { hour: '1', name: 'Evening' },    // 8 PM ET
    ];

    bennySchedules.forEach((schedule) => {
      new events.Rule(this, `BennyTraderSchedule${schedule.name}`, {
        schedule: events.Schedule.cron({ minute: '0', hour: schedule.hour }),
        targets: [
          new targets.EcsTask({
            cluster: props.cluster,
            taskDefinition: this.bennyTraderTask,
            role: eventRole,
            subnetSelection,
            assignPublicIp: true,
          }),
        ],
      });
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
