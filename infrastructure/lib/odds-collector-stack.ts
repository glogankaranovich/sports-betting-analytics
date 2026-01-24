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
  public readonly propsCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: OddsCollectorStackProps) {
    super(scope, id, props);

    // Reference existing secret
    const oddsApiSecret = secretsmanager.Secret.fromSecretNameV2(
      this, 
      'OddsApiSecret', 
      `sports-betting/odds-api-key-${props.environment}`
    );

    // Lambda function for game odds collection
    this.oddsCollectorFunction = new lambda.Function(this, 'OddsCollectorFunction', {
      functionName: `odds-collector-${props.environment}`,
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
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ODDS_API_SECRET_ARN: oddsApiSecret.secretArn,
        FORCE_UPDATE: '2025-01-01'
      }
    });

    // Lambda function for props collection
    this.propsCollectorFunction = new lambda.Function(this, 'PropsCollectorFunction', {
      functionName: `props-collector-${props.environment}`,
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
      memorySize: 2048,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ODDS_API_SECRET_ARN: oddsApiSecret.secretArn,
        FORCE_UPDATE: '2025-01-01'
      }
    });

    // Grant DynamoDB permissions to both functions
    const dynamoPolicy = new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:PutItem', 'dynamodb:UpdateItem', 'dynamodb:Scan', 'dynamodb:Query', 'dynamodb:GetItem'],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    });

    this.oddsCollectorFunction.addToRolePolicy(dynamoPolicy);
    this.propsCollectorFunction.addToRolePolicy(dynamoPolicy);

    // Grant Secrets Manager permissions to both functions
    oddsApiSecret.grantRead(this.oddsCollectorFunction);
    oddsApiSecret.grantRead(this.propsCollectorFunction);

    // Sports configuration with seasons
    const sportsConfig = [
      { key: 'basketball_nba', name: 'NBA', months: '10-6' },
      { key: 'americanfootball_nfl', name: 'NFL', months: '9-2' },
      { key: 'baseball_mlb', name: 'MLB', months: '3-10' },
      { key: 'icehockey_nhl', name: 'NHL', months: '10-6' },
      { key: 'soccer_epl', name: 'EPL', months: '8-5' }
    ];

    // Create EventBridge rules for game odds
    sportsConfig.forEach(sport => {
      new events.Rule(this, `${sport.name}OddsRule`, {
        schedule: events.Schedule.cron({ minute: '0', hour: '23', month: sport.months }),
        description: `Collect ${sport.name} game odds daily during season`,
        targets: [new targets.LambdaFunction(this.oddsCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport: sport.key })
        })]
      });
    });

    // Create EventBridge rules for props
    sportsConfig.forEach(sport => {
      new events.Rule(this, `${sport.name}PropsRule`, {
        schedule: events.Schedule.cron({ minute: '0', hour: '23', month: sport.months }),
        description: `Collect ${sport.name} player props daily during season`,
        targets: [new targets.LambdaFunction(this.propsCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport: sport.key, props_only: true })
        })]
      });
    });
  }
}
