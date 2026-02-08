import * as cdk from 'aws-cdk-lib';
import * as amplify from 'aws-cdk-lib/aws-amplify';
import { Construct } from 'constructs';

interface AmplifyStackProps extends cdk.StackProps {
  domainName?: string;
}

export class AmplifyStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: AmplifyStackProps) {
    super(scope, id, props);

    // Create Amplify app using CfnApp
    const amplifyApp = new amplify.CfnApp(this, 'BettingDashboard', {
      name: 'carpool-bets-dashboard',
      repository: 'https://github.com/your-github-username/sports-betting-analytics', // Update this
      oauthToken: cdk.SecretValue.secretsManager('github-token').unsafeUnwrap(), // Create this secret
      buildSpec: `
version: 1
frontend:
  phases:
    preBuild:
      commands:
        - cd frontend
        - echo "🔍 Installing dependencies..."
        - npm ci
    build:
      commands:
        - echo "🧪 Running frontend tests..."
        - npm run test:ci
        - echo "✅ Frontend tests passed!"
        - echo "🏗️ Building React app..."
        - npm run build
        - echo "✅ Build completed!"
  artifacts:
    baseDirectory: frontend/build
    files:
      - '**/*'
  cache:
    paths:
      - frontend/node_modules/**/*
      `,
    });

    // Beta branch - watches beta Git branch
    const betaBranch = new amplify.CfnBranch(this, 'BetaBranch', {
      appId: amplifyApp.attrAppId,
      branchName: 'beta',
      environmentVariables: [
        { name: 'REACT_APP_STAGE', value: 'beta' },
        { name: 'REACT_APP_API_URL', value: 'https://fgguxgxr4b.execute-api.us-east-1.amazonaws.com/prod' },
      ],
    });

    // Prod branch
    const prodBranch = new amplify.CfnBranch(this, 'ProdBranch', {
      appId: amplifyApp.attrAppId,
      branchName: 'prod',
      environmentVariables: [
        { name: 'REACT_APP_STAGE', value: 'prod' },
        { name: 'REACT_APP_API_URL', value: 'https://rk6h0zryz5.execute-api.us-east-1.amazonaws.com/prod' },
      ],
    });

    // Output URLs
    new cdk.CfnOutput(this, 'AmplifyBetaUrl', {
      value: `https://beta.${amplifyApp.attrDefaultDomain}`,
      description: 'Amplify App URL (beta branch - beta stage)',
    });

    new cdk.CfnOutput(this, 'AmplifyProdUrl', {
      value: `https://prod.${amplifyApp.attrDefaultDomain}`,
      description: 'Amplify App URL (prod branch - prod stage)',
    });

    // Add custom domain if provided
    if (props?.domainName) {
      const domain = new amplify.CfnDomain(this, 'CustomDomain', {
        appId: amplifyApp.attrAppId,
        domainName: props.domainName,
        subDomainSettings: [
          {
            branchName: prodBranch.branchName,
            prefix: '',
          },
          {
            branchName: prodBranch.branchName,
            prefix: 'www',
          },
          {
            branchName: betaBranch.branchName,
            prefix: 'beta',
          },
        ],
      });

      new cdk.CfnOutput(this, 'CustomDomainUrl', {
        value: `https://${props.domainName}`,
        description: 'Custom domain URL',
      });
    }
  }
}
