import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { CodePipeline, CodePipelineSource, CodeBuildStep } from 'aws-cdk-lib/pipelines';
import { LinuxBuildImage } from 'aws-cdk-lib/aws-codebuild';
import * as iam from 'aws-cdk-lib/aws-iam';
import { SportsBettingStage } from './sports-betting-stage';
import { ENVIRONMENTS } from '../lib/config/environments';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as snsSubscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as cloudwatchActions from 'aws-cdk-lib/aws-cloudwatch-actions';

export class SportsBettingPipelineStack extends cdk.Stack {
  private readonly pipelineName = 'SportsBettingPipeline';

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const pipeline = new CodePipeline(this, 'Pipeline', {
      pipelineName: this.pipelineName,
      crossAccountKeys: true,
      synth: new CodeBuildStep('Synth', {
        input: CodePipelineSource.gitHub('glogankaranovich/sports-betting-analytics', 'main', {
          authentication: cdk.SecretValue.secretsManager('github-token'),
        }),
        installCommands: [
          'npm install -g aws-cdk@2',
        ],
        commands: [
          'cd infrastructure',
          'npm ci',
          'npm run build',
          'cdk synth',
        ],
        primaryOutputDirectory: 'infrastructure/cdk.out',
        buildEnvironment: {
          buildImage: LinuxBuildImage.STANDARD_7_0,
        },
      }),
      selfMutationCodeBuildDefaults: {
        buildEnvironment: {
          buildImage: LinuxBuildImage.STANDARD_7_0,
        },
      },
    });

    // Staging stage
    const stagingStage = pipeline.addStage(new SportsBettingStage(this, 'Staging', {
      env: ENVIRONMENTS.staging,
      stage: 'staging',
    }));

    // Integration tests after staging deployment
    stagingStage.addPost(new CodeBuildStep('IntegrationTests', {
      commands: [
        'echo "🧪 Running integration tests against Staging environment..."',
        'cd backend',
        'python3 -m venv venv',
        './venv/bin/pip install -r requirements.txt',
        './venv/bin/pip install -r requirements-test.txt',
        'cd ..',
        'echo "Running API tests..."',
        './backend/venv/bin/python -m pytest tests/ -v',
        'echo "✅ Integration tests passed!"',
      ],
      buildEnvironment: {
        buildImage: LinuxBuildImage.STANDARD_7_0,
      },
      // Add permissions to assume cross-account role
      rolePolicyStatements: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['sts:AssumeRole'],
          resources: ['arn:aws:iam::352312075009:role/CrossAccountIntegrationTestRole-staging']
        })
      ]
    }));

    // Production stage (only deploys if staging tests pass)
    pipeline.addStage(new SportsBettingStage(this, 'Prod', {
      env: ENVIRONMENTS.prod,
      stage: 'prod',
    }));

    // Build pipeline for monitoring
    pipeline.buildPipeline();

    // Pipeline monitoring and alerts
    const pipelineAlertTopic = new sns.Topic(this, 'PipelineAlerts', {
      topicName: 'sports-betting-pipeline-alerts',
    });

    pipelineAlertTopic.addSubscription(
      new snsSubscriptions.EmailSubscription('glogankaranovich+sports-betting-pipeline@gmail.com')
    );

    const pipelineFailureAlarm = new cloudwatch.Alarm(this, 'PipelineFailureAlarm', {
      alarmName: 'sports-betting-pipeline-failures',
      alarmDescription: 'Alert when Sports Betting pipeline fails',
      metric: new cloudwatch.Metric({
        namespace: 'AWS/CodePipeline',
        metricName: 'FailedPipelineExecutions',
        dimensionsMap: {
          Pipeline: this.pipelineName,
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      }),
      threshold: 1,
      evaluationPeriods: 1,
    });

    pipelineFailureAlarm.addAlarmAction(new cloudwatchActions.SnsAction(pipelineAlertTopic));
  }
}
