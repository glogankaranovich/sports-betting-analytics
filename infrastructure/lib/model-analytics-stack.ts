import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as iam from "aws-cdk-lib/aws-iam";
import { Construct } from "constructs";

export interface ModelAnalyticsStackProps extends cdk.StackProps {
  betsTable: dynamodb.ITable;
}

export class ModelAnalyticsStack extends cdk.Stack {
  public readonly modelAnalyticsFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: ModelAnalyticsStackProps) {
    super(scope, id, props);

    // Model Analytics Lambda
    this.modelAnalyticsFunction = new lambda.Function(
      this,
      "ModelAnalyticsFunction",
      {
        runtime: lambda.Runtime.PYTHON_3_11,
        handler: "model_analytics.lambda_handler",
        code: lambda.Code.fromAsset("../backend", {
          bundling: {
            image: lambda.Runtime.PYTHON_3_11.bundlingImage,
            command: [
              "bash",
              "-c",
              "pip install -r requirements.txt -t /asset-output && cp -au . /asset-output",
            ],
          },
        }),
        timeout: cdk.Duration.minutes(5),
        memorySize: 512,
        environment: {
          DYNAMODB_TABLE: props.betsTable.tableName,
        },
      }
    );

    // Grant DynamoDB read/write permissions
    props.betsTable.grantReadWriteData(this.modelAnalyticsFunction);

    // Output
    new cdk.CfnOutput(this, "ModelAnalyticsFunctionName", {
      value: this.modelAnalyticsFunction.functionName,
      description: "Model Analytics Lambda Function Name",
    });
  }
}
