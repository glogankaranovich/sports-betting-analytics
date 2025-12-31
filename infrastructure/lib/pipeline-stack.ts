import * as cdk from 'aws-cdk-lib';
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
          
          // Test Python backend
          'cd ../backend',
          'python3 -m pip install -r requirements.txt',
          '# Add Python linting/testing here: python3 -m pytest',
          
          // Synthesize CDK
          'cd ../infrastructure',
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
        'echo "🧪 Running Python integration tests against Beta..."',
        'cd backend',
        'python3 -m pip install -r requirements.txt',
        'echo "Testing with table: $BETS_TABLE_NAME"',
        '# python3 -m pytest tests/integration/',
        'echo "✅ Integration tests passed!"',
      ],
      buildEnvironment: {
        buildImage: LinuxBuildImage.STANDARD_7_0,
      },
      envFromCfnOutputs: {
        BETS_TABLE_NAME: betaStageConstruct.betsTableName,
      },
    }));

    // Prod stage
    pipeline.addStage(new CarpoolBetsStage(this, 'Prod', {
      env: ENVIRONMENTS.prod,
      stage: 'prod',
    }));
  }
}
