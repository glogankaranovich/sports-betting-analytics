import * as cdk from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
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

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during NBA season (Oct-Jun)
    const dailyNbaRule = new events.Rule(this, "DailyNbaTeamStatsCollection", {
      schedule: events.Schedule.cron({
        minute: "0",
        hour: "7",
        month: "10-6",
      }),
      description: "Collect NBA team stats daily at 2 AM ET during NBA season",
    });

    dailyNbaRule.addTarget(
      new targets.LambdaFunction(this.teamStatsCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: "basketball_nba" }),
      })
    );

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during NFL season (Sep-Feb)
    const dailyNflRule = new events.Rule(this, "DailyNflTeamStatsCollection", {
      schedule: events.Schedule.cron({
        minute: "0",
        hour: "7",
        month: "9-2",
      }),
      description: "Collect NFL team stats daily at 2 AM ET during NFL season",
    });

    dailyNflRule.addTarget(
      new targets.LambdaFunction(this.teamStatsCollectorFunction, {
        event: events.RuleTargetInput.fromObject({
          sport: "americanfootball_nfl",
        }),
      })
    );

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during MLB season (Mar-Oct)
    const dailyMlbRule = new events.Rule(this, "DailyMlbTeamStatsCollection", {
      schedule: events.Schedule.cron({
        minute: "0",
        hour: "7",
        month: "3-10",
      }),
      description: "Collect MLB team stats daily at 2 AM ET during MLB season",
    });

    dailyMlbRule.addTarget(
      new targets.LambdaFunction(this.teamStatsCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: "baseball_mlb" }),
      })
    );

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during NHL season (Oct-Jun)
    const dailyNhlRule = new events.Rule(this, "DailyNhlTeamStatsCollection", {
      schedule: events.Schedule.cron({
        minute: "0",
        hour: "7",
        month: "10-6",
      }),
      description: "Collect NHL team stats daily at 2 AM ET during NHL season",
    });

    dailyNhlRule.addTarget(
      new targets.LambdaFunction(this.teamStatsCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: "icehockey_nhl" }),
      })
    );

    // EventBridge schedule to run daily at 2 AM ET (7 AM UTC) during EPL season (Aug-May)
    const dailyEplRule = new events.Rule(this, "DailyEplTeamStatsCollection", {
      schedule: events.Schedule.cron({
        minute: "0",
        hour: "7",
        month: "8-5",
      }),
      description: "Collect EPL team stats daily at 2 AM ET during EPL season",
    });

    dailyEplRule.addTarget(
      new targets.LambdaFunction(this.teamStatsCollectorFunction, {
        event: events.RuleTargetInput.fromObject({ sport: "soccer_epl" }),
      })
    );

    // Output
    new cdk.CfnOutput(this, "TeamStatsCollectorFunctionArn", {
      value: this.teamStatsCollectorFunction.functionArn,
    });
  }
}
