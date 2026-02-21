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

    // Lambda function for games endpoints (new modular handler)
    const gamesFunction = new lambda.Function(this, 'GamesApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'api.games.lambda_handler',
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
        ...getPlatformEnvironment(),
      }
    });
    gamesFunction.role?.addManagedPolicy(dynamoDbPolicy);

    // Lambda function for analyses endpoints (new modular handler)
    const analysesFunction = new lambda.Function(this, 'AnalysesApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'api.analyses.lambda_handler',
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
        ...getPlatformEnvironment(),
      }
    });
    analysesFunction.role?.addManagedPolicy(dynamoDbPolicy);

    // Lambda function for misc endpoints (new modular handler)
    const miscFunction = new lambda.Function(this, 'MiscApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'api.misc.lambda_handler',
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
        COMPLIANCE_TABLE_NAME: 'sports-betting-compliance-staging',
        ...getPlatformEnvironment(),
      }
    });
    miscFunction.role?.addManagedPolicy(dynamoDbPolicy);
    
    // Grant misc function permission to write to compliance table
    miscFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['dynamodb:PutItem', 'dynamodb:Query'],
      resources: ['arn:aws:dynamodb:*:*:table/sports-betting-compliance-staging']
    }));

    const analyticsFunction = new lambda.Function(this, 'AnalyticsApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'api.analytics.lambda_handler',
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
        ...getPlatformEnvironment(),
      }
    });
    analyticsFunction.role?.addManagedPolicy(dynamoDbPolicy);

    const userDataFunction = new lambda.Function(this, 'UserDataApiFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'api.user_data.lambda_handler',
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
        CUSTOM_DATA_TABLE: props.customDataTableName || `${props.environment === 'dev' ? 'Dev-' : ''}CustomData-CustomData`,
        CUSTOM_DATA_BUCKET: props.customDataBucketName || `${props.environment}-custom-data-bucket`,
        ...getPlatformEnvironment(),
      }
    });
    userDataFunction.role?.addManagedPolicy(dynamoDbPolicy);

    // Lambda function for bet collector API (legacy - will be deprecated)
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

    // Lambda integrations
    const gamesIntegration = new apigateway.LambdaIntegration(gamesFunction);
    const analysesIntegration = new apigateway.LambdaIntegration(analysesFunction);
    const miscIntegration = new apigateway.LambdaIntegration(miscFunction);
    const lambdaIntegration = new apigateway.LambdaIntegration(betCollectorApiFunction, {
      requestTemplates: { 'application/json': '{ "statusCode": "200" }' }
    });

    // API routes
    betCollectorApi.root.addMethod('ANY', lambdaIntegration);
    
    // Health endpoint (public) - using new misc handler
    const health = betCollectorApi.root.addResource('health');
    health.addMethod('GET', miscIntegration);

    // Protected endpoints (require auth if user pool exists)
    const methodOptions = authorizer ? {
      authorizer,
      authorizationType: apigateway.AuthorizationType.COGNITO,
    } : undefined;

    // Games endpoints (protected) - using new games handler
    const games = betCollectorApi.root.addResource('games');
    games.addMethod('GET', gamesIntegration, methodOptions);
    
    const gameById = games.addResource('{game_id}');
    gameById.addMethod('GET', lambdaIntegration, methodOptions); // Keep legacy for now

    // Sports endpoint (protected) - using new games handler
    const sports = betCollectorApi.root.addResource('sports');
    sports.addMethod('GET', gamesIntegration, methodOptions);

    // Bookmakers endpoint (protected) - using new games handler
    const bookmakers = betCollectorApi.root.addResource('bookmakers');
    bookmakers.addMethod('GET', gamesIntegration, methodOptions);

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

    // Player props endpoint (protected) - using new games handler
    const playerProps = betCollectorApi.root.addResource('player-props');
    playerProps.addMethod('GET', gamesIntegration, methodOptions);

    // Analyses endpoint (protected) - using new analyses handler
    const analyses = betCollectorApi.root.addResource('analyses');
    analyses.addMethod('GET', analysesIntegration, methodOptions);

    // Top analysis endpoint (protected) - using new analyses handler
    const topAnalysis = betCollectorApi.root.addResource('top-analysis');
    topAnalysis.addMethod('GET', analysesIntegration, methodOptions);

    // Analytics endpoints (protected) - using new analytics handler
    const analyticsIntegration = new apigateway.LambdaIntegration(analyticsFunction);
    
    const analytics = betCollectorApi.root.addResource('analytics');
    analytics.addMethod('GET', analyticsIntegration, methodOptions);

    const modelPerformance = betCollectorApi.root.addResource('model-performance');
    modelPerformance.addMethod('GET', analyticsIntegration, methodOptions);

    const modelComparison = betCollectorApi.root.addResource('model-comparison');
    modelComparison.addMethod('GET', analyticsIntegration, methodOptions);

    const modelRankings = betCollectorApi.root.addResource('model-rankings');
    modelRankings.addMethod('GET', analyticsIntegration, methodOptions);

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
    profile.addMethod('GET', userProfileIntegration, methodOptions);
    profile.addMethod('PUT', userProfileIntegration, methodOptions);
    
    const subscription = betCollectorApi.root.addResource('subscription');
    subscription.addMethod('GET', userProfileIntegration, methodOptions);
    
    const subscriptionUpgrade = subscription.addResource('upgrade');
    subscriptionUpgrade.addMethod('POST', userProfileIntegration, methodOptions);

    // User models and custom data endpoints (protected) - using new user data handler
    const userDataIntegration = new apigateway.LambdaIntegration(userDataFunction);

    const userModels = betCollectorApi.root.addResource('user-models');
    userModels.addMethod('GET', userDataIntegration, methodOptions);
    userModels.addMethod('POST', userDataIntegration, methodOptions);
    
    const userModelPredictions = userModels.addResource('predictions');
    userModelPredictions.addMethod('GET', userDataIntegration, methodOptions);
    
    const userModelById = userModels.addResource('{model_id}');
    userModelById.addMethod('GET', userDataIntegration, methodOptions);
    userModelById.addMethod('PUT', userDataIntegration, methodOptions);
    userModelById.addMethod('DELETE', userDataIntegration, methodOptions);
    
    const userModelBacktests = userModelById.addResource('backtests');
    userModelBacktests.addMethod('GET', userDataIntegration, methodOptions);
    userModelBacktests.addMethod('POST', userDataIntegration, methodOptions);
    
    const userModelPerformance = userModelById.addResource('performance');
    userModelPerformance.addMethod('GET', userDataIntegration, methodOptions);

    const backtests = betCollectorApi.root.addResource('backtests');
    const backtestById = backtests.addResource('{backtest_id}');
    backtestById.addMethod('GET', userDataIntegration, methodOptions);

    const customData = betCollectorApi.root.addResource('custom-data');
    customData.addMethod('GET', userDataIntegration, methodOptions);
    
    const customDataUpload = customData.addResource('upload');
    customDataUpload.addMethod('POST', userDataIntegration, methodOptions);
    
    const customDataById = customData.addResource('{dataset_id}');
    customDataById.addMethod('DELETE', userDataIntegration, methodOptions);

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

    // Benny dashboard endpoint (public - no auth required) - using new misc handler
    const benny = betCollectorApi.root.addResource('benny');
    const bennyDashboard = benny.addResource('dashboard');
    bennyDashboard.addMethod('GET', miscIntegration);

    // Compliance endpoint (public) - using new misc handler
    const compliance = betCollectorApi.root.addResource('compliance');
    const complianceLog = compliance.addResource('log');
    complianceLog.addMethod('POST', miscIntegration);

    // Export functions for monitoring
    this.betCollectorApiFunction = betCollectorApiFunction;
    this.userModelsApiFunction = userDataFunction;
    this.aiAgentApiFunction = aiAgentFunction;

    this.apiUrl = new cdk.CfnOutput(this, 'BetCollectorApiUrl', {
      value: betCollectorApi.url,
      description: 'Bet Collector API Gateway URL'
    });
  }
}
