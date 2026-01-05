import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class ComplianceStack extends cdk.Stack {
  public readonly complianceTable: dynamodb.Table;
  public readonly complianceApi: apigateway.RestApi;

  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // DynamoDB table for compliance logging
    this.complianceTable = new dynamodb.Table(this, 'ComplianceTable', {
      tableName: 'sports-betting-compliance-staging',
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      timeToLiveAttribute: 'ttl',
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.DESTROY
    });

    // Lambda function for compliance logging
    const complianceLoggerFunction = new lambda.Function(this, 'ComplianceLoggerFunction', {
      runtime: lambda.Runtime.PYTHON_3_9,
      handler: 'compliance_logger.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      environment: {
        COMPLIANCE_TABLE_NAME: this.complianceTable.tableName
      },
      timeout: cdk.Duration.seconds(30)
    });

    // Grant DynamoDB permissions
    this.complianceTable.grantReadWriteData(complianceLoggerFunction);

    // API Gateway for compliance endpoints
    this.complianceApi = new apigateway.RestApi(this, 'ComplianceApi', {
      restApiName: 'Sports Betting Compliance API',
      description: 'API for compliance logging and tracking',
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type', 'Authorization']
      }
    });

    // Compliance endpoints
    const complianceResource = this.complianceApi.root.addResource('compliance');
    const logResource = complianceResource.addResource('log');

    logResource.addMethod('POST', new apigateway.LambdaIntegration(complianceLoggerFunction));

    // Output the API URL
    new cdk.CfnOutput(this, 'ComplianceApiUrl', {
      value: this.complianceApi.url,
      description: 'Compliance API Gateway URL'
    });
  }
}
