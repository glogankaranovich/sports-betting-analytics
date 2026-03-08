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
          'npm install -g aws-cdk@2',
          'python3 -m pip install --upgrade pip',
        ],
        commands: [
          // Build infrastructure
          'cd infrastructure',
          'npm ci',
          'npm run build',
          'cdk synth',
        ],
        primaryOutputDirectory: 'infrastructure/cdk.out',
        buildEnvironment: {
          buildImage: LinuxBuildImage.STANDARD_7_0,
        },
        rolePolicyStatements: [
          new iam.PolicyStatement({
            actions: ['sts:AssumeRole'],
            resources: [
              `arn:aws:iam::${ENVIRONMENTS.beta.account}:role/cdk-*-lookup-role-*`,
              `arn:aws:iam::${ENVIRONMENTS.prod.account}:role/cdk-*-lookup-role-*`,
            ],
          }),
        ],
      }),
    });

    // Beta stage
    const betaStageConstruct = new CarpoolBetsStage(this, 'Beta', {
      env: ENVIRONMENTS.beta,
      stage: 'beta',
    });
    
    // Build and push Docker image for Beta after ECR repo is created
    const betaStage = pipeline.addStage(betaStageConstruct, {
      post: [
        new CodeBuildStep('BuildDockerImageBeta', {
          commands: [
            'echo "Building Docker image for Beta..."',
            'export AWS_ACCOUNT_ID=' + ENVIRONMENTS.beta.account,
            'export ECR_REPO_URI=$AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/beta-batch-jobs',
            'aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO_URI',
            'docker build -t beta-batch-jobs:latest .',
            'docker tag beta-batch-jobs:latest $ECR_REPO_URI:latest',
            'docker push $ECR_REPO_URI:latest',
            'echo "Docker image pushed to $ECR_REPO_URI:latest"',
          ],
          buildEnvironment: {
            buildImage: LinuxBuildImage.STANDARD_7_0,
            privileged: true,
          },
          rolePolicyStatements: [
            new iam.PolicyStatement({
              actions: [
                'ecr:GetAuthorizationToken',
                'ecr:BatchCheckLayerAvailability',
                'ecr:GetDownloadUrlForLayer',
                'ecr:BatchGetImage',
                'ecr:PutImage',
                'ecr:InitiateLayerUpload',
                'ecr:UploadLayerPart',
                'ecr:CompleteLayerUpload',
              ],
              resources: ['*'],
            }),
          ],
        }),
      ],
    });

    // Integration tests (Python) - Run all integration tests
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
        'echo "Running all integration tests..."',
        'python3 -m pytest tests/integration/ -v --tb=short'
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
    const prodStageConstruct = new CarpoolBetsStage(this, 'Prod', {
      env: ENVIRONMENTS.prod,
      stage: 'prod',
    });
    
    // Build and push Docker image for Prod after ECR repo is created
    const prodStage = pipeline.addStage(prodStageConstruct, {
      post: [
        new CodeBuildStep('BuildDockerImageProd', {
          commands: [
            'echo "Building Docker image for Prod..."',
            'export AWS_ACCOUNT_ID=' + ENVIRONMENTS.prod.account,
            'export ECR_REPO_URI=$AWS_ACCOUNT_ID.dkr.ecr.us-east-1.amazonaws.com/prod-batch-jobs',
            'aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin $ECR_REPO_URI',
            'docker build -t prod-batch-jobs:latest .',
            'docker tag prod-batch-jobs:latest $ECR_REPO_URI:latest',
            'docker push $ECR_REPO_URI:latest',
            'echo "Docker image pushed to $ECR_REPO_URI:latest"',
          ],
          buildEnvironment: {
            buildImage: LinuxBuildImage.STANDARD_7_0,
            privileged: true,
          },
          rolePolicyStatements: [
            new iam.PolicyStatement({
              actions: [
                'ecr:GetAuthorizationToken',
                'ecr:BatchCheckLayerAvailability',
                'ecr:GetDownloadUrlForLayer',
                'ecr:BatchGetImage',
                'ecr:PutImage',
                'ecr:InitiateLayerUpload',
                'ecr:UploadLayerPart',
                'ecr:CompleteLayerUpload',
              ],
              resources: ['*'],
            }),
          ],
        }),
      ],
    });

    // Integration tests for Prod (Python) with automatic rollback - TEMPORARILY DISABLED
    // TODO: Re-enable after fixing integration test schema issues
    // prodStage.addPost(new CodeBuildStep('ProdIntegrationTestsWithRollback', {
    //   commands: [
    //     'echo "🧪 Running integration tests against Prod..."',
    //     'cd backend',
    //     'pip3 install -r requirements.txt',
    //     // Run integration tests
    //     'if python3 tests/integration/test_api_integration.py; then',
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
