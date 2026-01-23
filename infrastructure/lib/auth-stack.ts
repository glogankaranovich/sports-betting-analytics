import * as cdk from 'aws-cdk-lib';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import { Construct } from 'constructs';

export interface AuthStackProps extends cdk.StackProps {
  environment: string;
}

export class AuthStack extends cdk.Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    // Environment-specific callback URLs
    const getCallbackUrls = (env: string): string[] => {
      const urls = ['http://localhost:3000']; // Always include local dev
      
      if (env === 'dev') {
        // Dev environment - only local
        return urls;
      } else if (env === 'beta') {
        // Beta environment - local + beta Amplify
        urls.push('https://beta.d1234567890.amplifyapp.com'); // Update with actual domain
        return urls;
      } else if (env === 'prod') {
        // Prod environment - local + prod Amplify
        urls.push('https://prod.d1234567890.amplifyapp.com'); // Update with actual domain
        return urls;
      }
      
      return urls;
    };

    // Create Cognito User Pool
    this.userPool = new cognito.UserPool(this, 'UserPool', {
      userPoolName: `carpool-bets-users-${props.environment}`,
      selfSignUpEnabled: false,
      signInAliases: {
        email: true,
      },
      autoVerify: {
        email: false,
      },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: false,
      },
      accountRecovery: cognito.AccountRecovery.NONE,
      removalPolicy: cdk.RemovalPolicy.DESTROY, // For dev/testing
    });

    // Create User Pool Client
    this.userPoolClient = new cognito.UserPoolClient(this, 'UserPoolClient', {
      userPool: this.userPool,
      userPoolClientName: `carpool-bets-client-${props.environment}`,
      generateSecret: false, // For frontend apps
      authFlows: {
        userPassword: true,
        userSrp: true,
        adminUserPassword: true, // Enable admin auth flow for testing
      },
      oAuth: {
        flows: {
          authorizationCodeGrant: true,
        },
        scopes: [
          cognito.OAuthScope.EMAIL,
          cognito.OAuthScope.OPENID,
          cognito.OAuthScope.PROFILE,
        ],
        callbackUrls: getCallbackUrls(props.environment),
        logoutUrls: getCallbackUrls(props.environment),
      },
    });

    // Outputs
    new cdk.CfnOutput(this, 'UserPoolId', {
      value: this.userPool.userPoolId,
      description: 'Cognito User Pool ID',
    });

    new cdk.CfnOutput(this, 'UserPoolClientId', {
      value: this.userPoolClient.userPoolClientId,
      description: 'Cognito User Pool Client ID',
    });

    new cdk.CfnOutput(this, 'UserPoolDomain', {
      value: `https://cognito-idp.${this.region}.amazonaws.com/${this.userPool.userPoolId}`,
      description: 'Cognito User Pool Domain',
    });
  }
}
