import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import { CodePipeline, CodePipelineSource, CodeBuildStep } from 'aws-cdk-lib/pipelines';
import { LinuxBuildImage } from 'aws-cdk-lib/aws-codebuild';
import { CarpoolBetsStage } from './carpool-bets-stage';
import { ENVIRONMENTS } from './config/environments';

export class CarpoolBetsPipelineStack extends cdk.Stack {
  private readonly pipelineName = 'CarpoolBetsPipeline';

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
          'npm install -g aws-cdk@2',  // CDK for infrastructure
          'python3 -m pip install --upgrade pip',  // Python for backend
        ],
        commands: [
          // Build infrastructure (TypeScript/CDK)
          'cd infrastructure',
          'npm ci',
          'npm run build',
          
          // Synthesize CDK (skip backend for now)
          'cdk synth',
        ],
        primaryOutputDirectory: 'infrastructure/cdk.out',
        buildEnvironment: {
          buildImage: LinuxBuildImage.STANDARD_7_0,
        },
      }),
    });

    // Beta stage
    const betaStageConstruct = new CarpoolBetsStage(this, 'Beta', {
      env: ENVIRONMENTS.beta,
      stage: 'beta',
    });
    const betaStage = pipeline.addStage(betaStageConstruct);

    // Integration tests (Python)
    betaStage.addPost(new CodeBuildStep('IntegrationTests', {
      commands: [
        'echo "🧪 Running integration tests against Beta..."',
        'ls -la',
        'ls -la backend/',
        'cd backend',
        'ls -la',
        'python3 -m pip install -r requirements.txt',
        'python3 test_integration.py'
      ],
      buildEnvironment: {
        buildImage: LinuxBuildImage.STANDARD_7_0,
      },
      env: {
        ENVIRONMENT: 'beta'
      },
      rolePolicyStatements: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['lambda:InvokeFunction', 'lambda:ListFunctions'],
          resources: ['*']
        }),
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: ['dynamodb:Scan', 'dynamodb:Query'],
          resources: ['*']
        })
      ]
    }));

    // Prod stage
    pipeline.addStage(new CarpoolBetsStage(this, 'Prod', {
      env: ENVIRONMENTS.prod,
      stage: 'prod',
    }));
  }
}
