import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';

export interface BetCollectorApiStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
  userPool?: cognito.UserPool;
}

export class BetCollectorApiStack extends cdk.Stack {
  public readonly apiUrl: cdk.CfnOutput;

  constructor(scope: Construct, id: string, props: BetCollectorApiStackProps) {
    super(scope, id, props);

    // Lambda function for bet collector API
    const betCollectorApiFunction = new lambda.Function(this, 'BetCollectorApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'api_handler.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ]
        }
      }),
      timeout: cdk.Duration.seconds(30),
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ENVIRONMENT: props.environment
      }
    });

    // Grant DynamoDB permissions
    betCollectorApiFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Scan',
        'dynamodb:Query',
        'dynamodb:GetItem',
        'dynamodb:PutItem'
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    }));

    // API Gateway for bet collector
    const betCollectorApi = new apigateway.RestApi(this, 'BetCollectorApi', {
      restApiName: `Bet Collector API - ${props.environment}`,
      description: `API for accessing collected betting data in ${props.environment} environment`,
      defaultCorsPreflightOptions: {
        allowOrigins: ['http://localhost:3000', 'https://*.amplifyapp.com'],
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization', 'X-Amz-Date', 'X-Api-Key', 'X-Amz-Security-Token'],
        allowCredentials: true,
      }
    });

    // Cognito authorizer (if user pool provided)
    let authorizer: apigateway.CognitoUserPoolsAuthorizer | undefined;
    if (props.userPool) {
      authorizer = new apigateway.CognitoUserPoolsAuthorizer(this, 'CognitoAuthorizer', {
        cognitoUserPools: [props.userPool],
        authorizerName: `carpool-bets-authorizer-${props.environment}`,
      });
    }

    // Lambda integration
    const lambdaIntegration = new apigateway.LambdaIntegration(betCollectorApiFunction, {
      requestTemplates: { 'application/json': '{ "statusCode": "200" }' }
    });

    // API routes
    betCollectorApi.root.addMethod('ANY', lambdaIntegration);
    
    // Health endpoint (public)
    const health = betCollectorApi.root.addResource('health');
    health.addMethod('GET', lambdaIntegration);

    // Protected endpoints (require auth if user pool exists)
    const methodOptions = authorizer ? {
      authorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    } : undefined;

    // Games endpoints (protected)
    const games = betCollectorApi.root.addResource('games');
    games.addMethod('GET', lambdaIntegration, methodOptions);
    
    const gameById = games.addResource('{game_id}');
    gameById.addMethod('GET', lambdaIntegration, methodOptions);

    // Sports endpoint (protected)
    const sports = betCollectorApi.root.addResource('sports');
    sports.addMethod('GET', lambdaIntegration, methodOptions);

    // Bookmakers endpoint (protected)
    const bookmakers = betCollectorApi.root.addResource('bookmakers');
    bookmakers.addMethod('GET', lambdaIntegration, methodOptions);

    // Predictions endpoint (protected)
    const predictions = betCollectorApi.root.addResource('predictions');
    predictions.addMethod('GET', lambdaIntegration, methodOptions);

    // Stored predictions endpoint (protected)
    const storedPredictions = betCollectorApi.root.addResource('stored-predictions');
    storedPredictions.addMethod('GET', lambdaIntegration, methodOptions);

    // Game predictions endpoint (protected)
    const gamePredictions = betCollectorApi.root.addResource('game-predictions');
    gamePredictions.addMethod('GET', lambdaIntegration, methodOptions);

    // Prop predictions endpoint (protected)
    const propPredictions = betCollectorApi.root.addResource('prop-predictions');
    propPredictions.addMethod('GET', lambdaIntegration, methodOptions);

    // Player props endpoint (protected)
    const playerProps = betCollectorApi.root.addResource('player-props');
    playerProps.addMethod('GET', lambdaIntegration, methodOptions);

    // Analyses endpoint (protected)
    const analyses = betCollectorApi.root.addResource('analyses');
    analyses.addMethod('GET', lambdaIntegration, methodOptions);

    // Top analysis endpoint (protected)
    const topAnalysis = betCollectorApi.root.addResource('top-analysis');
    topAnalysis.addMethod('GET', lambdaIntegration, methodOptions);

    // Analytics endpoint (protected)
    const analytics = betCollectorApi.root.addResource('analytics');
    analytics.addMethod('GET', lambdaIntegration, methodOptions);

    // Model performance endpoint (protected)
    const modelPerformance = betCollectorApi.root.addResource('model-performance');
    modelPerformance.addMethod('GET', lambdaIntegration, methodOptions);

    this.apiUrl = new cdk.CfnOutput(this, 'BetCollectorApiUrl', {
      value: betCollectorApi.url,
      description: 'Bet Collector API Gateway URL'
    });
  }
}
