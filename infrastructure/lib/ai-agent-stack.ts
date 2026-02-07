import * as cdk from "aws-cdk-lib";
import * as apigateway from "aws-cdk-lib/aws-apigateway";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { Construct } from "constructs";

interface AIAgentStackProps extends cdk.StackProps {
  stage: string;
  dynamodbTableName: string;
}

export class AIAgentStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: AIAgentStackProps) {
    super(scope, id, props);

    const { stage, dynamodbTableName } = props;

    // AI Agent Lambda
    const aiAgentLambda = new lambda.Function(this, "AIAgentFunction", {
      functionName: `ai-agent-${stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "ai_agent_api.lambda_handler",
      code: lambda.Code.fromAsset("../backend", {
        exclude: ["tests", "*.pyc", "__pycache__", ".pytest_cache"],
      }),
      timeout: cdk.Duration.seconds(30),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: dynamodbTableName,
        STAGE: stage,
      },
    });

    // Grant DynamoDB permissions
    aiAgentLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query",
          "dynamodb:Scan",
        ],
        resources: [
          `arn:aws:dynamodb:${this.region}:${this.account}:table/${dynamodbTableName}`,
          `arn:aws:dynamodb:${this.region}:${this.account}:table/${dynamodbTableName}/index/*`,
        ],
      })
    );

    // Grant Bedrock permissions
    aiAgentLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        resources: [
          `arn:aws:bedrock:${this.region}::foundation-model/anthropic.claude-3-5-sonnet-20240620-v1:0`,
        ],
      })
    );

    // API Gateway
    const api = new apigateway.RestApi(this, "AIAgentAPI", {
      restApiName: `ai-agent-api-${stage}`,
      description: "AI Agent API for natural language model creation",
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ["Content-Type", "Authorization"],
      },
    });

    // /ai-agent resource
    const aiAgentResource = api.root.addResource("ai-agent");

    // /ai-agent/chat endpoint
    const chatResource = aiAgentResource.addResource("chat");
    chatResource.addMethod(
      "POST",
      new apigateway.LambdaIntegration(aiAgentLambda)
    );

    // Outputs
    new cdk.CfnOutput(this, "AIAgentAPIUrl", {
      value: api.url,
      description: "AI Agent API URL",
    });

    new cdk.CfnOutput(this, "AIAgentLambdaArn", {
      value: aiAgentLambda.functionArn,
      description: "AI Agent Lambda ARN",
    });
  }
}
