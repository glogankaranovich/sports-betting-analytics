import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface ModelAnalyticsScheduleStackProps extends cdk.StackProps {
  modelAnalyticsFunction: lambda.IFunction;
}

export class ModelAnalyticsScheduleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: ModelAnalyticsScheduleStackProps) {
    super(scope, id, props);

    new events.Rule(this, 'AnalyticsRule', {
      schedule: events.Schedule.rate(cdk.Duration.hours(4)),
      targets: [new targets.LambdaFunction(props.modelAnalyticsFunction)],
    });
  }
}
