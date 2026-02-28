import * as cdk from 'aws-cdk-lib';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
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

    // Dead Letter Queue for failed invocations
    const dlq = new sqs.Queue(this, 'OddsCollectorDLQ', {
      queueName: `odds-collector-dlq-${props.environment}`,
      retentionPeriod: cdk.Duration.days(14),
    });

    const sports = [
      { key: 'basketball_nba', name: 'NBA' },
      { key: 'americanfootball_nfl', name: 'NFL' },
      { key: 'baseball_mlb', name: 'MLB' },
      { key: 'icehockey_nhl', name: 'NHL' },
      { key: 'soccer_epl', name: 'EPL' },
      { key: 'basketball_mens-college-basketball', name: 'NCAAMBB' },
      { key: 'basketball_womens-college-basketball', name: 'NCAAWBB' },
      { key: 'football_college-football', name: 'NCAAFB' }
    ];

    // Odds collection - every 4 hours for each sport (staggered by 15 minutes)
    const oddsSchedules = [
      'cron(0 */4 * * ? *)',   // NBA: 00:00, 04:00, 08:00, 12:00, 16:00, 20:00 UTC
      'cron(15 */4 * * ? *)',  // NFL: 00:15, 04:15, 08:15, 12:15, 16:15, 20:15 UTC
      'cron(30 */4 * * ? *)',  // MLB: 00:30, 04:30, 08:30, 12:30, 16:30, 20:30 UTC
      'cron(45 */4 * * ? *)',  // NHL: 00:45, 04:45, 08:45, 12:45, 16:45, 20:45 UTC
      'cron(50 */4 * * ? *)',  // EPL: 00:50, 04:50, 08:50, 12:50, 16:50, 20:50 UTC
      'cron(55 */4 * * ? *)',  // NCAAMBB: 00:55, 04:55, 08:55, 12:55, 16:55, 20:55 UTC
      'cron(5 */4 * * ? *)',   // NCAAWBB: 00:05, 04:05, 08:05, 12:05, 16:05, 20:05 UTC
      'cron(10 */4 * * ? *)',  // NCAAFB: 00:10, 04:10, 08:10, 12:10, 16:10, 20:10 UTC
    ];

    sports.forEach((sport, index) => {
      new events.Rule(this, `OddsRule${sport.name}`, {
        schedule: events.Schedule.expression(oddsSchedules[index]),
        description: `Collect ${sport.name} game odds every 4 hours`,
        targets: [new targets.LambdaFunction(oddsCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport: sport.key }),
          deadLetterQueue: dlq,
          maxEventAge: cdk.Duration.hours(1),
          retryAttempts: 0,
        })]
      });
    });

    // Props collection - every 8 hours for each sport (staggered by 15 minutes)
    const propsSchedules = [
      'cron(0 */8 * * ? *)',   // NBA: 00:00, 08:00, 16:00 UTC
      'cron(15 */8 * * ? *)',  // NFL: 00:15, 08:15, 16:15 UTC
      'cron(30 */8 * * ? *)',  // MLB: 00:30, 08:30, 16:30 UTC
      'cron(45 */8 * * ? *)',  // NHL: 00:45, 08:45, 16:45 UTC
      'cron(50 */8 * * ? *)',  // EPL: 00:50, 08:50, 16:50 UTC
      'cron(55 */8 * * ? *)',  // NCAAMBB: 00:55, 08:55, 16:55 UTC
      'cron(5 */8 * * ? *)',   // NCAAWBB: 00:05, 08:05, 16:05 UTC
      'cron(10 */8 * * ? *)',  // NCAAFB: 00:10, 08:10, 16:10 UTC
    ];

    sports.forEach((sport, index) => {
      new events.Rule(this, `PropsRule${sport.name}`, {
        schedule: events.Schedule.expression(propsSchedules[index]),
        description: `Collect ${sport.name} props every 8 hours`,
        targets: [new targets.LambdaFunction(propsCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport: sport.key, props_only: true }),
          deadLetterQueue: dlq,
          maxEventAge: cdk.Duration.hours(1),
          retryAttempts: 0,
        })]
      });
    });
  }
}
