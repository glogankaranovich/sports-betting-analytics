import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import { Construct } from "constructs";
import * as path from "path";
import { getSupportedSportsArray } from './utils/constants';

export interface SeasonStatsCollectorStackProps extends cdk.StackProps {
  environment: string;
  table: dynamodb.ITable;
}

export class SeasonStatsCollectorStack extends cdk.Stack {
  public readonly seasonStatsCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: SeasonStatsCollectorStackProps) {
    super(scope, id, props);

    // Season Stats Collector Lambda (uses ESPN statistics API)
    this.seasonStatsCollectorFunction = new lambda.Function(this, "SeasonStatsCollectorFunction", {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "team_season_stats_handler.lambda_handler",
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
      timeout: cdk.Duration.minutes(10),
      memorySize: 1024,
      environment: {
        DYNAMODB_TABLE: props.table.tableName,
      },
    });

    // Grant DynamoDB permissions
    props.table.grantReadWriteData(this.seasonStatsCollectorFunction);

    // Run weekly on Mondays at 3 AM ET (8 AM UTC) - season stats don't change daily
    const weeklyRule = new events.Rule(this, "WeeklySeasonStatsCollection", {
      schedule: events.Schedule.cron({
        minute: "0",
        hour: "8",
        weekDay: "MON",
      }),
      description: "Collect season stats weekly for all sports",
    });

    // Trigger for all sports at once
    weeklyRule.addTarget(
      new targets.LambdaFunction(this.seasonStatsCollectorFunction, {
        event: events.RuleTargetInput.fromObject({
          sports: getSupportedSportsArray()
        }),
      })
    );

    // Output
    new cdk.CfnOutput(this, "SeasonStatsCollectorFunctionArn", {
      value: this.seasonStatsCollectorFunction.functionArn,
    });
  }
}
