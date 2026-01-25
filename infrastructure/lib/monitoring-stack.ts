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
  propsCollectorFunction: lambda.IFunction;
  scheduleCollectorFunction: lambda.IFunction;
  analysisGeneratorFunctions: lambda.IFunction[];
  insightGeneratorFunctions: lambda.IFunction[];
  playerStatsCollectorFunction: lambda.IFunction;
  teamStatsCollectorFunction: lambda.IFunction;
  injuryCollectorFunction: lambda.IFunction;
  outcomeCollectorFunction: lambda.IFunction;
  modelAnalyticsFunction: lambda.IFunction;
  seasonManagerFunction: lambda.IFunction;
  complianceLoggerFunction: lambda.IFunction;
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
    const propsMetrics = createLambdaMetrics(props.propsCollectorFunction, 'PropsCollector');
    const scheduleMetrics = createLambdaMetrics(props.scheduleCollectorFunction, 'ScheduleCollector');
    const playerStatsMetrics = createLambdaMetrics(props.playerStatsCollectorFunction, 'PlayerStatsCollector');
    const teamStatsMetrics = createLambdaMetrics(props.teamStatsCollectorFunction, 'TeamStatsCollector');
    const outcomeMetrics = createLambdaMetrics(props.outcomeCollectorFunction, 'OutcomeCollector');
    const modelAnalyticsMetrics = createLambdaMetrics(props.modelAnalyticsFunction, 'ModelAnalytics');
    const seasonManagerMetrics = createLambdaMetrics(props.seasonManagerFunction, 'SeasonManager');
    const complianceMetrics = createLambdaMetrics(props.complianceLoggerFunction, 'ComplianceLogger');
    
    // Create metrics for analysis generators (one per sport)
    const analysisMetrics = props.analysisGeneratorFunctions.flatMap((fn, i) => 
      createLambdaMetrics(fn, `AnalysisGen${['NBA','NFL','MLB','NHL','EPL'][i]}`)
    );
    
    // Create metrics for insight generators (one per sport)
    const insightMetrics = props.insightGeneratorFunctions.flatMap((fn, i) => 
      createLambdaMetrics(fn, `InsightGen${['NBA','NFL','MLB','NHL','EPL'][i]}`)
    );

    // Flatten metrics arrays
    const allInvocations = [
      oddsMetrics.invocations,
      propsMetrics.invocations,
      scheduleMetrics.invocations,
      ...analysisMetrics.map(m => m.invocations),
      ...insightMetrics.map(m => m.invocations),
      playerStatsMetrics.invocations,
      teamStatsMetrics.invocations,
      outcomeMetrics.invocations,
      modelAnalyticsMetrics.invocations,
      seasonManagerMetrics.invocations,
      complianceMetrics.invocations,
    ];

    const allErrors = [
      oddsMetrics.errors,
      propsMetrics.errors,
      scheduleMetrics.errors,
      ...analysisMetrics.map(m => m.errors),
      ...insightMetrics.map(m => m.errors),
      playerStatsMetrics.errors,
      teamStatsMetrics.errors,
      outcomeMetrics.errors,
      modelAnalyticsMetrics.errors,
      seasonManagerMetrics.errors,
      complianceMetrics.errors,
    ];

    const allDurations = [
      oddsMetrics.duration,
      propsMetrics.duration,
      scheduleMetrics.duration,
      ...analysisMetrics.map(m => m.duration),
      ...insightMetrics.map(m => m.duration),
      playerStatsMetrics.duration,
      teamStatsMetrics.duration,
      outcomeMetrics.duration,
      modelAnalyticsMetrics.duration,
      seasonManagerMetrics.duration,
      complianceMetrics.duration,
    ];

    const allThrottles = [
      oddsMetrics.throttles,
      propsMetrics.throttles,
      scheduleMetrics.throttles,
      ...analysisMetrics.map(m => m.throttles),
      ...insightMetrics.map(m => m.throttles),
      playerStatsMetrics.throttles,
      teamStatsMetrics.throttles,
      outcomeMetrics.throttles,
      modelAnalyticsMetrics.throttles,
      seasonManagerMetrics.throttles,
      complianceMetrics.throttles,
    ];

    // Add widgets to dashboard
    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Invocations',
        left: allInvocations,
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Errors',
        left: allErrors,
        width: 12,
      })
    );

    dashboard.addWidgets(
      new cloudwatch.GraphWidget({
        title: 'Lambda Duration (ms)',
        left: allDurations,
        width: 12,
      }),
      new cloudwatch.GraphWidget({
        title: 'Lambda Throttles',
        left: allThrottles,
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
