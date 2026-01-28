import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface OddsCollectorScheduleStackProps extends cdk.StackProps {
  environment: string;
  sport: { key: string; name: string; months: string };
  oddsCollectorFunction: lambda.IFunction;
  propsCollectorFunction: lambda.IFunction;
}

export class OddsCollectorScheduleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: OddsCollectorScheduleStackProps) {
    super(scope, id, props);

    const { sport, oddsCollectorFunction, propsCollectorFunction } = props;

    // Run every 2 hours
    const hours = ['0', '2', '4', '6', '8', '10', '12', '14', '16', '18', '20', '22'];

    // Odds collection rules
    hours.forEach(hour => {
      new events.Rule(this, `OddsRule${hour}`, {
        schedule: events.Schedule.cron({ minute: '0', hour, month: sport.months }),
        description: `Collect ${sport.name} game odds at ${hour}:00 UTC`,
        targets: [new targets.LambdaFunction(oddsCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport: sport.key })
        })]
      });
    });

    // Props collection rules
    hours.forEach(hour => {
      new events.Rule(this, `PropsRule${hour}`, {
        schedule: events.Schedule.cron({ minute: '15', hour, month: sport.months }),
        description: `Collect ${sport.name} props at ${hour}:15 UTC`,
        targets: [new targets.LambdaFunction(propsCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport: sport.key, props_only: true })
        })]
      });
    });
  }
}
