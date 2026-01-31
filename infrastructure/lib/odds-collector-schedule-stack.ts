import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import { Construct } from 'constructs';

export interface OddsCollectorScheduleStackProps extends cdk.StackProps {
  environment: string;
  oddsCollectorFunction: lambda.IFunction;
  propsCollectorFunction: lambda.IFunction;
}

export class OddsCollectorScheduleStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: OddsCollectorScheduleStackProps) {
    super(scope, id, props);

    const { oddsCollectorFunction, propsCollectorFunction } = props;

    const sports = [
      { key: 'basketball_nba', name: 'NBA' },
      { key: 'americanfootball_nfl', name: 'NFL' },
      { key: 'baseball_mlb', name: 'MLB' },
      { key: 'icehockey_nhl', name: 'NHL' },
      { key: 'soccer_epl', name: 'EPL' }
    ];

    // Odds collection - every 4 hours for each sport
    sports.forEach(sport => {
      new events.Rule(this, `OddsRule${sport.name}`, {
        schedule: events.Schedule.rate(cdk.Duration.hours(4)),
        description: `Collect ${sport.name} game odds every 4 hours`,
        targets: [new targets.LambdaFunction(oddsCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport: sport.key })
        })]
      });
    });

    // Props collection - every 4 hours for each sport
    sports.forEach(sport => {
      new events.Rule(this, `PropsRule${sport.name}`, {
        schedule: events.Schedule.rate(cdk.Duration.hours(4)),
        description: `Collect ${sport.name} props every 4 hours`,
        targets: [new targets.LambdaFunction(propsCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport: sport.key, props_only: true })
        })]
      });
    });
  }
}
