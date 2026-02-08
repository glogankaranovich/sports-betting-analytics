import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface BennyTraderScheduleStackProps extends cdk.StackProps {
  bennyTraderFunction: lambda.IFunction;
}

export class BennyTraderScheduleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: BennyTraderScheduleStackProps) {
    super(scope, id, props);

    new events.Rule(this, 'BennyTraderRule', {
      schedule: events.Schedule.cron({ hour: '14', minute: '0' }),
      targets: [new targets.LambdaFunction(props.bennyTraderFunction)],
    });
  }
}
