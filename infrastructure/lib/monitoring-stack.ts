import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatch_actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sns_subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface MonitoringStackProps extends cdk.StackProps {
  environment: string;
  oddsCollectorFunction: lambda.IFunction;
  analysisGeneratorFunction: lambda.IFunction;
  insightGeneratorFunction: lambda.IFunction;
  playerStatsCollectorFunction: lambda.IFunction;
  teamStatsCollectorFunction: lambda.IFunction;
  outcomeCollectorFunction: lambda.IFunction;
}

export class MonitoringStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    // SNS Topic for alarms
    const alarmTopic = new sns.Topic(this, 'AlarmTopic', {
      displayName: `Carpool Bets Alarms - ${props.environment}`,
      topicName: `carpool-bets-alarms-${props.environment}`,
    });

    // Add email subscription
    alarmTopic.addSubscription(
      new sns_subscriptions.EmailSubscription('glogankaranovich@gmail.com')
    );

    // CloudWatch Dashboard
    const dashboard = new cloudwatch.Dashboard(this, 'Dashboard', {
      dashboardName: `CarpoolBets-${props.environment}`,
    });

    // Helper function to create Lambda metrics
    const createLambdaMetrics = (fn: lambda.IFunction, name: string) => {
      const errors = fn.metricErrors({
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      });

      const throttles = fn.metricThrottles({
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      });

      const duration = fn.metricDuration({
        statistic: 'Average',
        period: cdk.Duration.minutes(5),
      });

      const invocations = fn.metricInvocations({
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      });

      // Create alarm for errors
      const errorAlarm = new cloudwatch.Alarm(this, `${name}ErrorAlarm`, {
        metric: errors,
        threshold: 1,
        evaluationPeriods: 1,
        alarmDescription: `${name} has errors`,
        alarmName: `${props.environment}-${name}-Errors`,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });
      errorAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(alarmTopic));

      // Create alarm for throttles
      const throttleAlarm = new cloudwatch.Alarm(this, `${name}ThrottleAlarm`, {
        metric: throttles,
        threshold: 1,
        evaluationPeriods: 1,
        alarmDescription: `${name} is being throttled`,
        alarmName: `${props.environment}-${name}-Throttles`,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });
      throttleAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(alarmTopic));

      return { errors, throttles, duration, invocations };
    };

    // Create metrics for all functions
    const oddsMetrics = createLambdaMetrics(props.oddsCollectorFunction, 'OddsCollector');
    const analysisMetrics = createLambdaMetrics(props.analysisGeneratorFunction, 'AnalysisGenerator');
    const insightMetrics = createLambdaMetrics(props.insightGeneratorFunction, 'InsightGenerator');
    const playerStatsMetrics = createLambdaMetrics(props.playerStatsCollectorFunction, 'PlayerStatsCollector');
    const teamStatsMetrics = createLambdaMetrics(props.teamStatsCollectorFunction, 'TeamStatsCollector');
    const outcomeMetrics = createLambdaMetrics(props.outcomeCollectorFunction, 'OutcomeCollector');

    // Add widgets to dashboard
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Invocations',
        left: [
          oddsMetrics.invocations,
          analysisMetrics.invocations,
          insightMetrics.invocations,
          playerStatsMetrics.invocations,
          teamStatsMetrics.invocations,
          outcomeMetrics.invocations,
        ],
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Errors',
        left: [
          oddsMetrics.errors,
          analysisMetrics.errors,
          insightMetrics.errors,
          playerStatsMetrics.errors,
          teamStatsMetrics.errors,
          outcomeMetrics.errors,
        ],
        width: 12,
      })
    );

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Duration (ms)',
        left: [
          oddsMetrics.duration,
          analysisMetrics.duration,
          insightMetrics.duration,
          playerStatsMetrics.duration,
          teamStatsMetrics.duration,
          outcomeMetrics.duration,
        ],
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Throttles',
        left: [
          oddsMetrics.throttles,
          analysisMetrics.throttles,
          insightMetrics.throttles,
          playerStatsMetrics.throttles,
          teamStatsMetrics.throttles,
          outcomeMetrics.throttles,
        ],
        width: 12,
      })
    );

    // Outputs
    new cdk.CfnOutput(this, 'DashboardUrl', {
      value: `https://console.aws.amazon.com/cloudwatch/home?region=${this.region}#dashboards:name=${dashboard.dashboardName}`,
      description: 'CloudWatch Dashboard URL',
    });

    new cdk.CfnOutput(this, 'AlarmTopicArn', {
      value: alarmTopic.topicArn,
      description: 'SNS Topic ARN for alarms',
    });
  }
}
