import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import { Construct } from 'constructs';

interface AIAgentStackProps extends cdk.StackProps {
  environment: string;
  dynamodbTable: cdk.aws_dynamodb.ITable;
  api: apigateway.RestApi;
  authorizer?: apigateway.CognitoUserPoolsAuthorizer;
}

export class AIAgentStack extends cdk.Stack {
  public readonly aiAgentFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: AIAgentStackProps) {
    super(scope, id, props);

    // AI Agent Lambda
    this.aiAgentFunction = new lambda.Function(this, 'AIAgentFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'ai_agent.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        exclude: ['tests', '__pycache__', '*.pyc', '.pytest_cache'],
      }),
      timeout: cdk.Duration.seconds(60),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.dynamodbTable.tableName,
        ENVIRONMENT: props.environment,
      },
    });

    // Grant DynamoDB access
    props.dynamodbTable.grantReadData(this.aiAgentFunction);

    // Grant Bedrock access
    this.aiAgentFunction.addToRolePolicy(
      new iam.PolicyStatement({
        effect: iam.Effect.ALLOW,
        actions: ['bedrock:InvokeModel'],
        resources: [
          `arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-sonnet-20240229-v1:0`,
        ],
      })
    );

    // Add API endpoint
    const aiAgent = props.api.root.addResource('ai-agent');
    const chat = aiAgent.addResource('chat');

    const methodOptions = props.authorizer
      ? {
          authorizer: props.authorizer,
          authorizationType: apigateway.AuthorizationType.COGNITO,
        }
      : undefined;

    chat.addMethod(
      'POST',
      new apigateway.LambdaIntegration(this.aiAgentFunction),
      methodOptions
    );

    // Outputs
    new cdk.CfnOutput(this, 'AIAgentFunctionName', {
      value: this.aiAgentFunction.functionName,
      description: 'AI Agent Lambda Function Name',
    });
  }
}
