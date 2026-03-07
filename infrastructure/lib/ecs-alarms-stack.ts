#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export interface EcsAlarmsStackProps extends cdk.StackProps {
  stage: string;
  cluster: ecs.ICluster;
  alarmTopic: sns.ITopic;
  propsCollectorLogGroup: logs.ILogGroup;
  analysisGeneratorLogGroup: logs.ILogGroup;
  bennyTraderLogGroup: logs.ILogGroup;
}

export class EcsAlarmsStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EcsAlarmsStackProps) {
    super(scope, id, props);

    // Metric filter for errors in props collector logs
    const propsErrorMetric = new logs.MetricFilter(this, 'PropsCollectorErrors', {
      logGroup: props.propsCollectorLogGroup,
      filterPattern: logs.FilterPattern.anyTerm('Error', 'Exception', 'Traceback', 'error occurred'),
      metricNamespace: 'ECS/BatchJobs',
      metricName: 'PropsCollectorErrors',
      metricValue: '1',
      defaultValue: 0,
    });

    new cloudwatch.Alarm(this, 'PropsCollectorErrorAlarm', {
      alarmName: `${props.stage}-props-collector-errors`,
      metric: propsErrorMetric.metric(),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      alarmDescription: 'Alert when props collector encounters errors',
    }).addAlarmAction(new actions.SnsAction(props.alarmTopic));

    // Metric filter for errors in analysis generator logs
    const analysisErrorMetric = new logs.MetricFilter(this, 'AnalysisGeneratorErrors', {
      logGroup: props.analysisGeneratorLogGroup,
      filterPattern: logs.FilterPattern.anyTerm('Error', 'Exception', 'Traceback', 'error occurred'),
      metricNamespace: 'ECS/BatchJobs',
      metricName: 'AnalysisGeneratorErrors',
      metricValue: '1',
      defaultValue: 0,
    });

    new cloudwatch.Alarm(this, 'AnalysisGeneratorErrorAlarm', {
      alarmName: `${props.stage}-analysis-generator-errors`,
      metric: analysisErrorMetric.metric(),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      alarmDescription: 'Alert when analysis generator encounters errors',
    }).addAlarmAction(new actions.SnsAction(props.alarmTopic));

    // Metric filter for errors in benny trader logs
    const bennyErrorMetric = new logs.MetricFilter(this, 'BennyTraderErrors', {
      logGroup: props.bennyTraderLogGroup,
      filterPattern: logs.FilterPattern.anyTerm('Error', 'Exception', 'Traceback', 'error occurred'),
      metricNamespace: 'ECS/BatchJobs',
      metricName: 'BennyTraderErrors',
      metricValue: '1',
      defaultValue: 0,
    });

    new cloudwatch.Alarm(this, 'BennyTraderErrorAlarm', {
      alarmName: `${props.stage}-benny-trader-errors`,
      metric: bennyErrorMetric.metric(),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
      alarmDescription: 'Alert when benny trader encounters errors',
    }).addAlarmAction(new actions.SnsAction(props.alarmTopic));

    // Alarm if props collector hasn't run in 7 hours (should run every 6 hours)
    new cloudwatch.Alarm(this, 'PropsCollectorNotRunningAlarm', {
      alarmName: `${props.stage}-props-collector-not-running`,
      metric: new cloudwatch.Metric({
        namespace: 'AWS/Logs',
        metricName: 'IncomingLogEvents',
        dimensionsMap: {
          LogGroupName: props.propsCollectorLogGroup.logGroupName,
        },
        statistic: 'Sum',
        period: cdk.Duration.hours(7),
      }),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
      alarmDescription: 'Alert when props collector has not run in 7 hours',
    }).addAlarmAction(new actions.SnsAction(props.alarmTopic));

    // Alarm if analysis generator hasn't run in 5 hours (should run every 4 hours)
    new cloudwatch.Alarm(this, 'AnalysisGeneratorNotRunningAlarm', {
      alarmName: `${props.stage}-analysis-generator-not-running`,
      metric: new cloudwatch.Metric({
        namespace: 'AWS/Logs',
        metricName: 'IncomingLogEvents',
        dimensionsMap: {
          LogGroupName: props.analysisGeneratorLogGroup.logGroupName,
        },
        statistic: 'Sum',
        period: cdk.Duration.hours(5),
      }),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
      alarmDescription: 'Alert when analysis generator has not run in 5 hours',
    }).addAlarmAction(new actions.SnsAction(props.alarmTopic));

    // Alarm if benny trader hasn't run in 26 hours (should run daily)
    new cloudwatch.Alarm(this, 'BennyTraderNotRunningAlarm', {
      alarmName: `${props.stage}-benny-trader-not-running`,
      metric: new cloudwatch.Metric({
        namespace: 'AWS/Logs',
        metricName: 'IncomingLogEvents',
        dimensionsMap: {
          LogGroupName: props.bennyTraderLogGroup.logGroupName,
        },
        statistic: 'Sum',
        period: cdk.Duration.hours(26),
      }),
      threshold: 1,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.BREACHING,
      alarmDescription: 'Alert when benny trader has not run in 26 hours',
    }).addAlarmAction(new actions.SnsAction(props.alarmTopic));

    // Alarm for task failures (non-zero exit codes)
    const taskFailureAlarm = new cloudwatch.Alarm(this, 'EcsTaskFailureAlarm', {
      alarmName: `${props.stage}-ecs-task-failures`,
      metric: new cloudwatch.Metric({
        namespace: 'AWS/ECS',
        metricName: 'TaskCount',
        dimensionsMap: {
          ClusterName: props.cluster.clusterName,
        },
        statistic: 'Sum',
        period: cdk.Duration.minutes(5),
      }),
      threshold: 0,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.LESS_THAN_OR_EQUAL_TO_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      alarmDescription: 'Alert when ECS tasks fail to run',
    });

    taskFailureAlarm.addAlarmAction(new actions.SnsAction(props.alarmTopic));
  }
}
