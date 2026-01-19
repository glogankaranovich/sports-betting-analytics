import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { Construct } from "constructs";
import * as path from "path";

export interface TeamStatsCollectorStackProps extends cdk.StackProps {
  environment: string;
  table: dynamodb.ITable;
}

export class TeamStatsCollectorStack extends cdk.Stack {
  public readonly teamStatsCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: TeamStatsCollectorStackProps) {
    super(scope, id, props);

    // Team Stats Collector Lambda
    this.teamStatsCollectorFunction = new lambda.Function(this, "TeamStatsCollectorFunction", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "team_stats_collector.lambda_handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../../backend"), {
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
        DYNAMODB_TABLE: props.table.tableName,
      },
    });

    // Grant DynamoDB permissions
    props.table.grantReadWriteData(this.teamStatsCollectorFunction);

    // Output
    new cdk.CfnOutput(this, "TeamStatsCollectorFunctionArn", {
      value: this.teamStatsCollectorFunction.functionArn,
    });
  }
}
