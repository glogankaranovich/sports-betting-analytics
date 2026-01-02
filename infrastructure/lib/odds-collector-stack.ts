import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';

export interface OddsCollectorStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
}

export class OddsCollectorStack extends cdk.Stack {
  public readonly oddsCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: OddsCollectorStackProps) {
    super(scope, id, props);

    // Reference existing secret
    const oddsApiSecret = secretsmanager.Secret.fromSecretNameV2(
      this, 
      'OddsApiSecret', 
      `sports-betting/odds-api-key-${props.environment}`
    );

    // Lambda function for odds collection with Docker bundling
    this.oddsCollectorFunction = new lambda.Function(this, 'OddsCollectorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'odds_collector.lambda_handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ]
        }
      }),
      timeout: cdk.Duration.minutes(15),
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ODDS_API_SECRET_ARN: oddsApiSecret.secretArn,
        FORCE_UPDATE: '2025-01-01'
      }
    });

    // Grant DynamoDB permissions
    this.oddsCollectorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:PutItem', 'dynamodb:UpdateItem', 'dynamodb:Scan', 'dynamodb:Query', 'dynamodb:GetItem'],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    }));

    // Grant Secrets Manager permissions
    oddsApiSecret.grantRead(this.oddsCollectorFunction);

    // Schedule NBA odds collection twice daily (8 AM and 8 PM)
    const nbaOddsRule = new events.Rule(this, 'NBAOddsCollectionSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '8,20' })
    });

    nbaOddsRule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'basketball_nba' })
    }));

    // Schedule NFL odds collection twice daily (9 AM and 9 PM)
    const nflOddsRule = new events.Rule(this, 'NFLOddsCollectionSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '9,21' })
    });

    nflOddsRule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'americanfootball_nfl' })
    }));

    // Schedule NBA props collection twice daily (10 AM and 10 PM)
    const nbaPropsRule = new events.Rule(this, 'NBAPropsCollectionSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '10,22' })
    });

    nbaPropsRule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'basketball_nba', props_only: true })
    }));

    // Schedule NFL props collection twice daily (11 AM and 11 PM)
    const nflPropsRule = new events.Rule(this, 'NFLPropsCollectionSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '11,23' })
    });

    nflPropsRule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'americanfootball_nfl', props_only: true })
    }));
  }
}
