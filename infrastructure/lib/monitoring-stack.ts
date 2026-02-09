import * as cdk from 'aws-cdk-lib';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatch_actions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sns_subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';

export interface MonitoringStackProps extends cdk.StackProps {
  environment: string;
  oddsCollectorFunction: lambda.IFunction;
  propsCollectorFunction: lambda.IFunction;
  scheduleCollectorFunction: lambda.IFunction;
  analysisGeneratorFunctions: lambda.IFunction[];
  playerStatsCollectorFunction: lambda.IFunction;
  teamStatsCollectorFunction: lambda.IFunction;
  injuryCollectorFunction: lambda.IFunction;
  outcomeCollectorFunction: lambda.IFunction;
  modelAnalyticsFunction: lambda.IFunction;
  seasonManagerFunction: lambda.IFunction;
  complianceLoggerFunction: lambda.IFunction;
  bennyTraderFunction: lambda.IFunction;
  betCollectorApiFunction: lambda.IFunction;
  userModelsApiFunction: lambda.IFunction;
  aiAgentApiFunction: lambda.IFunction;
  modelExecutorFunction: lambda.IFunction;
  queueLoaderFunction: lambda.IFunction;
  dynamodbTables?: dynamodb.ITable[];
  apiGateways?: apigateway.IRestApi[];
  dlQueues?: sqs.IQueue[];
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
        evaluationPeriods: 10,
        alarmDescription: `${name} has errors`,
        alarmName: `${props.environment}-${name}-Errors`,
        treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
      });
      errorAlarm.addAlarmAction(new cloudwatch_actions.SnsAction(alarmTopic));

      // Create alarm for throttles
      const throttleAlarm = new cloudwatch.Alarm(this, `${name}ThrottleAlarm`, {
        metric: throttles,
        threshold: 1,
        evaluationPeriods: 10,
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
    const bennyTraderMetrics = createLambdaMetrics(props.bennyTraderFunction, 'BennyTrader');
    const betApiMetrics = createLambdaMetrics(props.betCollectorApiFunction, 'BetCollectorAPI');
    const userModelsApiMetrics = createLambdaMetrics(props.userModelsApiFunction, 'UserModelsAPI');
    const aiAgentApiMetrics = createLambdaMetrics(props.aiAgentApiFunction, 'AIAgentAPI');
    const modelExecutorMetrics = createLambdaMetrics(props.modelExecutorFunction, 'ModelExecutor');
    const queueLoaderMetrics = createLambdaMetrics(props.queueLoaderFunction, 'QueueLoader');
    
    // Create metrics for analysis generators (one per sport)
    const analysisMetrics = props.analysisGeneratorFunctions.flatMap((fn, i) => 
      createLambdaMetrics(fn, `AnalysisGen${['NBA','NFL','MLB','NHL','EPL'][i]}`)
    );

    // Flatten metrics arrays
    const allInvocations = [
      oddsMetrics.invocations,
      propsMetrics.invocations,
      scheduleMetrics.invocations,
      ...analysisMetrics.map(m => m.invocations),
      playerStatsMetrics.invocations,
      teamStatsMetrics.invocations,
      outcomeMetrics.invocations,
      modelAnalyticsMetrics.invocations,
      seasonManagerMetrics.invocations,
      complianceMetrics.invocations,
      bennyTraderMetrics.invocations,
      betApiMetrics.invocations,
      userModelsApiMetrics.invocations,
      aiAgentApiMetrics.invocations,
      modelExecutorMetrics.invocations,
      queueLoaderMetrics.invocations,
    ];

    const allErrors = [
      oddsMetrics.errors,
      propsMetrics.errors,
      scheduleMetrics.errors,
      ...analysisMetrics.map(m => m.errors),
      playerStatsMetrics.errors,
      teamStatsMetrics.errors,
      outcomeMetrics.errors,
      modelAnalyticsMetrics.errors,
      seasonManagerMetrics.errors,
      complianceMetrics.errors,
      bennyTraderMetrics.errors,
      betApiMetrics.errors,
      userModelsApiMetrics.errors,
      aiAgentApiMetrics.errors,
      modelExecutorMetrics.errors,
      queueLoaderMetrics.errors,
    ];

    const allDurations = [
      oddsMetrics.duration,
      propsMetrics.duration,
      scheduleMetrics.duration,
      ...analysisMetrics.map(m => m.duration),
      playerStatsMetrics.duration,
      teamStatsMetrics.duration,
      outcomeMetrics.duration,
      modelAnalyticsMetrics.duration,
      seasonManagerMetrics.duration,
      complianceMetrics.duration,
      bennyTraderMetrics.duration,
      betApiMetrics.duration,
      userModelsApiMetrics.duration,
      aiAgentApiMetrics.duration,
      modelExecutorMetrics.duration,
      queueLoaderMetrics.duration,
    ];

    const allThrottles = [
      oddsMetrics.throttles,
      propsMetrics.throttles,
      scheduleMetrics.throttles,
      ...analysisMetrics.map(m => m.throttles),
      playerStatsMetrics.throttles,
      teamStatsMetrics.throttles,
      outcomeMetrics.throttles,
      modelAnalyticsMetrics.throttles,
      seasonManagerMetrics.throttles,
      complianceMetrics.throttles,
      bennyTraderMetrics.throttles,
      betApiMetrics.throttles,
      userModelsApiMetrics.throttles,
      aiAgentApiMetrics.throttles,
      modelExecutorMetrics.throttles,
      queueLoaderMetrics.throttles,
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

    // DynamoDB alarms
    if (props.dynamodbTables) {
      props.dynamodbTables.forEach((table, i) => {
        const readThrottle = new cloudwatch.Alarm(this, `DDB${i}ReadThrottle`, {
          metric: table.metricUserErrors({ dimensionsMap: { TableName: table.tableName, Operation: 'GetItem' } }),
          threshold: 10,
          evaluationPeriods: 2,
          alarmName: `${props.environment}-DDB-ReadThrottle-${i}`,
        });
        readThrottle.addAlarmAction(new cloudwatch_actions.SnsAction(alarmTopic));
      });
    }

    // API Gateway alarms
    if (props.apiGateways) {
      props.apiGateways.forEach((api, i) => {
        const serverErrors = new cloudwatch.Alarm(this, `API${i}5xxErrors`, {
          metric: new cloudwatch.Metric({
            namespace: 'AWS/ApiGateway',
            metricName: '5XXError',
            dimensionsMap: { ApiName: api.restApiName },
            statistic: 'Sum',
            period: cdk.Duration.minutes(5),
          }),
          threshold: 5,
          evaluationPeriods: 2,
          alarmName: `${props.environment}-API-5xxErrors-${i}`,
        });
        serverErrors.addAlarmAction(new cloudwatch_actions.SnsAction(alarmTopic));
      });
    }

    // SQS DLQ alarms
    if (props.dlQueues) {
      props.dlQueues.forEach((queue, i) => {
        const dlqDepth = new cloudwatch.Alarm(this, `DLQ${i}Depth`, {
          metric: queue.metricApproximateNumberOfMessagesVisible(),
          threshold: 1,
          evaluationPeriods: 1,
          alarmName: `${props.environment}-DLQ-Depth-${i}`,
        });
        dlqDepth.addAlarmAction(new cloudwatch_actions.SnsAction(alarmTopic));
      });
    }
  }
}
