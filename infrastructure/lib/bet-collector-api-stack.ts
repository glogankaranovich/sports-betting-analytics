import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as cognito from 'aws-cdk-lib/aws-cognito';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import { Construct } from 'constructs';
import { getPlatformEnvironment } from './utils/constants';

export interface BetCollectorApiStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
  userModelsTableName?: string;
  modelPredictionsTableName?: string;
  customDataTableName?: string;
  customDataBucketName?: string;
  customDataTable?: dynamodb.ITable;
  customDataBucket?: any;
  userPool?: cognito.UserPool;
  modelAnalyticsFunction?: lambda.IFunction;
}

export class BetCollectorApiStack extends cdk.Stack {
  public readonly apiUrl: cdk.CfnOutput;
  public readonly betCollectorApiFunction: lambda.Function;
  public readonly userModelsApiFunction: lambda.Function;
  public readonly aiAgentApiFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: BetCollectorApiStackProps) {
    super(scope, id, props);

    // Create managed policy for DynamoDB access (avoids inline policy size limit)
    const dynamoDbPolicy = new iam.ManagedPolicy(this, 'BetCollectorDynamoDbPolicy', {
      statements: [
        new iam.PolicyStatement({
          effect: iam.Effect.ALLOW,
          actions: [
            'dynamodb:Scan',
            'dynamodb:Query',
            'dynamodb:GetItem',
            'dynamodb:PutItem',
            'dynamodb:UpdateItem',
            'dynamodb:DeleteItem'
          ],
          resources: [
            `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}*`,
            `arn:aws:dynamodb:${this.region}:${this.account}:table/Dev-UserModels-*`
          ]
        })
      ]
    });

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
        ENVIRONMENT: props.environment,
        MODEL_ANALYTICS_FUNCTION: props.modelAnalyticsFunction?.functionName || '',
        CUSTOM_DATA_TABLE: props.customDataTableName || `${props.environment === 'dev' ? 'Dev-' : ''}CustomData-CustomData`,
        CUSTOM_DATA_BUCKET: props.customDataBucketName || `${props.environment}-custom-data-bucket`,
        ...getPlatformEnvironment(),
      }
    });

    // Attach managed policy
    betCollectorApiFunction.role?.addManagedPolicy(dynamoDbPolicy);

    // Grant Lambda invoke permissions for model analytics
    if (props.modelAnalyticsFunction) {
      props.modelAnalyticsFunction.grantInvoke(betCollectorApiFunction);
    }

    // Grant custom data permissions
    if (props.customDataTable) {
      props.customDataTable.grantReadWriteData(betCollectorApiFunction);
    }
    if (props.customDataBucket) {
      props.customDataBucket.grantReadWrite(betCollectorApiFunction);
    }

    // API Gateway for bet collector
    const betCollectorApi = new apigateway.RestApi(this, 'BetCollectorApi', {
      restApiName: `Bet Collector API - ${props.environment}`,
      description: `API for accessing collected betting data in ${props.environment} environment`,
      deploy: true,
      deployOptions: {
        stageName: 'prod',
      },
      defaultCorsPreflightOptions: {
        allowOrigins: ['http://localhost:3000', 'https://*.amplifyapp.com', 'https://beta.carpoolbets.com', 'https://carpoolbets.com', 'https://www.carpoolbets.com'],
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

    // Model comparison endpoint (protected)
    const modelComparison = betCollectorApi.root.addResource('model-comparison');
    modelComparison.addMethod('GET', lambdaIntegration, methodOptions);

    // Model rankings endpoint (protected)
    const modelRankings = betCollectorApi.root.addResource('model-rankings');
    modelRankings.addMethod('GET', lambdaIntegration, methodOptions);

    // Separate Lambda for user profile/subscription to avoid policy size limits
    const userProfileFunction = new lambda.Function(this, 'UserProfileApiFunction', {
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
        ENVIRONMENT: props.environment,
      }
    });

    userProfileFunction.role?.addManagedPolicy(dynamoDbPolicy);

    const userProfileIntegration = new apigateway.LambdaIntegration(userProfileFunction);

    // User profile and subscription endpoints (protected, using separate Lambda)
    const profile = betCollectorApi.root.addResource('profile');
    profile.addMethod('OPTIONS', userProfileIntegration); // CORS preflight
    profile.addMethod('GET', userProfileIntegration, methodOptions);
    profile.addMethod('PUT', userProfileIntegration, methodOptions);
    
    const subscription = betCollectorApi.root.addResource('subscription');
    subscription.addMethod('OPTIONS', userProfileIntegration); // CORS preflight
    subscription.addMethod('GET', userProfileIntegration, methodOptions);
    
    const subscriptionUpgrade = subscription.addResource('upgrade');
    subscriptionUpgrade.addMethod('OPTIONS', userProfileIntegration); // CORS preflight
    subscriptionUpgrade.addMethod('POST', userProfileIntegration, methodOptions);

    // Separate Lambda for user models to avoid policy size limits
    const userModelsFunction = new lambda.Function(this, 'UserModelsApiFunction', {
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
        ENVIRONMENT: props.environment,
        USER_MODELS_TABLE: props.userModelsTableName || `${props.environment === 'dev' ? 'Dev-' : ''}UserModels-UserModels`,
        MODEL_PREDICTIONS_TABLE: props.modelPredictionsTableName || `${props.environment === 'dev' ? 'Dev-' : ''}UserModels-ModelPredictions`,
      }
    });

    // Attach managed policy
    userModelsFunction.role?.addManagedPolicy(dynamoDbPolicy);

    const userModelsIntegration = new apigateway.LambdaIntegration(userModelsFunction);

    // User models endpoints (protected, using separate Lambda)
    const userModels = betCollectorApi.root.addResource('user-models');
    userModels.addMethod('GET', userModelsIntegration, methodOptions);  // List models
    userModels.addMethod('POST', userModelsIntegration, methodOptions); // Create model
    
    const userModelPredictions = userModels.addResource('predictions');
    userModelPredictions.addMethod('GET', userModelsIntegration, methodOptions); // Get all predictions
    
    const userModelById = userModels.addResource('{model_id}');
    userModelById.addMethod('GET', userModelsIntegration, methodOptions);    // Get model
    userModelById.addMethod('PUT', userModelsIntegration, methodOptions);    // Update model
    userModelById.addMethod('DELETE', userModelsIntegration, methodOptions); // Delete model
    
    const userModelBacktests = userModelById.addResource('backtests');
    userModelBacktests.addMethod('GET', userModelsIntegration, methodOptions);  // List backtests
    userModelBacktests.addMethod('POST', userModelsIntegration, methodOptions); // Create backtest
    
    const userModelPerformance = userModelById.addResource('performance');
    userModelPerformance.addMethod('GET', userModelsIntegration, methodOptions); // Get model performance

    // AI Agent Lambda
    const aiAgentFunction = new lambda.Function(this, 'AIAgentFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'ai_agent.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ENVIRONMENT: props.environment,
      },
    });

    // Grant Bedrock access
    aiAgentFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel'],
        resources: ['arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0'],
      })
    );

    // AI Agent endpoint (protected)
    const aiAgent = betCollectorApi.root.addResource('ai-agent');
    const chat = aiAgent.addResource('chat');
    chat.addMethod('POST', new apigateway.LambdaIntegration(aiAgentFunction), methodOptions);

    // Benny dashboard endpoint (public - no auth required)
    const benny = betCollectorApi.root.addResource('benny');
    const bennyDashboard = benny.addResource('dashboard');
    bennyDashboard.addMethod('GET', lambdaIntegration);

    // Export functions for monitoring
    this.betCollectorApiFunction = betCollectorApiFunction;
    this.userModelsApiFunction = userModelsFunction;
    this.aiAgentApiFunction = aiAgentFunction;

    this.apiUrl = new cdk.CfnOutput(this, 'BetCollectorApiUrl', {
      value: betCollectorApi.url,
      description: 'Bet Collector API Gateway URL'
    });
  }
}
