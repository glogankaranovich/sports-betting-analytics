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
          
          // Synthesize CDK
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

    // Integration tests (Python) - Re-enabled after fixing schema issues
    betaStage.addPost(new CodeBuildStep('IntegrationTests', {
      commands: [
        'echo "🧪 Running integration tests against Beta..."',
        // Assume the integration test role in the beta account
        `aws sts assume-role --role-arn arn:aws:iam::${ENVIRONMENTS.beta.account}:role/PipelineIntegrationTestRole --role-session-name integration-test > /tmp/creds.json`,
        'export AWS_ACCESS_KEY_ID=$(cat /tmp/creds.json | jq -r .Credentials.AccessKeyId)',
        'export AWS_SECRET_ACCESS_KEY=$(cat /tmp/creds.json | jq -r .Credentials.SecretAccessKey)',
        'export AWS_SESSION_TOKEN=$(cat /tmp/creds.json | jq -r .Credentials.SessionToken)',
        'cd backend',
        'python3 -m pip install -r requirements.txt',
        'echo "Testing Lambda and DynamoDB integration..."',
        'python3 test_integration.py',
        'echo "Testing API endpoints..."',
        'python3 test_api_integration.py'
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
          actions: ['sts:AssumeRole'],
          resources: [`arn:aws:iam::${ENVIRONMENTS.beta.account}:role/PipelineIntegrationTestRole`]
        })
      ]
    }));

    // Prod stage
    const prodStage = pipeline.addStage(new CarpoolBetsStage(this, 'Prod', {
      env: ENVIRONMENTS.prod,
      stage: 'prod',
    }));

    // Integration tests for Prod (Python) with automatic rollback - TEMPORARILY DISABLED
    // TODO: Re-enable after fixing integration test schema issues
    // prodStage.addPost(new CodeBuildStep('ProdIntegrationTestsWithRollback', {
    //   commands: [
    //     'echo "🧪 Running integration tests against Prod..."',
    //     'cd backend',
    //     'pip3 install -r requirements.txt',
    //     // Run integration tests
    //     'if python3 test_api_integration.py; then',
    //     '  echo "✅ Prod integration tests passed!"',
    //     'else',
    //     '  echo "❌ Prod integration tests FAILED - initiating rollback..."',
    //     '  # Get the stack names that were just deployed',
    //     '  echo "Rolling back Prod-Auth stack..."',
    //     '  aws cloudformation cancel-update-stack --stack-name Prod-Auth --region us-east-1 || true',
    //     '  echo "Rolling back Prod-BetCollectorApi stack..."', 
    //     '  aws cloudformation cancel-update-stack --stack-name Prod-BetCollectorApi --region us-east-1 || true',
    //     '  echo "Rolling back Prod-OddsCollector stack..."',
    //     '  aws cloudformation cancel-update-stack --stack-name Prod-OddsCollector --region us-east-1 || true',
    //     '  echo "Rolling back Prod-DynamoDB stack..."',
    //     '  aws cloudformation cancel-update-stack --stack-name Prod-DynamoDB --region us-east-1 || true',
    //     '  echo "🔄 Rollback initiated - check CloudFormation console"',
    //     '  exit 1',
    //     'fi'
    //   ],
    //   env: {
    //     ENVIRONMENT: 'prod'
    //   },
    //   rolePolicyStatements: [
    //     new iam.PolicyStatement({
    //       actions: [
    //         'sts:AssumeRole',
    //         'cloudformation:CancelUpdateStack',
    //         'cloudformation:DescribeStacks'
    //       ],
    //       resources: [
    //         // 'arn:aws:iam::' + ENVIRONMENTS.prod.account + ':role/PipelineIntegrationTestRole',
    //         // 'arn:aws:cloudformation:us-east-1:' + ENVIRONMENTS.prod.account + ':stack/Prod-*/*'
    //       ]
    //     })
    //   ]
    // }));
  }
}
