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
            'pip install -r requirements.txt -t /asset-output && cp *.py /asset-output/ && cp -r ml /asset-output/ 2>/dev/null || true'
          ]
        }
      }),
      timeout: cdk.Duration.minutes(15),
      memorySize: 2048, // Increased from default 128MB for faster processing
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

    // EventBridge schedules for automated odds collection
    
    // Schedule NBA odds collection daily at 6 PM ET (11 PM UTC) - October through June
    const nbaOddsRule = new events.Rule(this, 'NBAOddsCollectionSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '23', month: '10-6' }),
      description: 'Collect NBA odds daily at 6 PM ET during NBA season (Oct-Jun)'
    });

    nbaOddsRule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'basketball_nba' })
    }));

    // Schedule NFL odds collection daily at 6 PM ET (11 PM UTC) - September through February
    const nflOddsRule = new events.Rule(this, 'NFLOddsCollectionSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '23', month: '9-2' }),
      description: 'Collect NFL odds daily at 6 PM ET during NFL season (Sep-Feb)'
    });

    nflOddsRule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'americanfootball_nfl' })
    }));

    // Schedule NBA props collection daily at 6 PM ET (11 PM UTC) - October through June
    const nbaPropsRule = new events.Rule(this, 'NBAPropsCollectionSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '23', month: '10-6' }),
      description: 'Collect NBA props daily at 6 PM ET during NBA season (Oct-Jun)'
    });

    nbaPropsRule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'basketball_nba', props_only: true })
    }));

    // Schedule NFL props collection daily at 6 PM ET (11 PM UTC) - September through February
    const nflPropsRule = new events.Rule(this, 'NFLPropsCollectionSchedule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '23', month: '9-2' }),
      description: 'Collect NFL props daily at 6 PM ET during NFL season (Sep-Feb)'
    });

    nflPropsRule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction, {
      event: events.RuleTargetInput.fromObject({ sport: 'americanfootball_nfl', props_only: true })
    }));
  }
}
