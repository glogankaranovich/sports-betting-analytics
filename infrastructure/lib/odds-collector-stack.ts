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
      timeout: cdk.Duration.minutes(5),
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ODDS_API_SECRET_ARN: oddsApiSecret.secretArn
      }
    });

    // Grant DynamoDB permissions
    this.oddsCollectorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:PutItem', 'dynamodb:UpdateItem', 'dynamodb:Scan'],
      resources: [`arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`]
    }));

    // Grant Secrets Manager permissions
    oddsApiSecret.grantRead(this.oddsCollectorFunction);

    // Schedule to run every 4 hours
    const rule = new events.Rule(this, 'OddsCollectionSchedule', {
      schedule: events.Schedule.rate(cdk.Duration.hours(4))
    });

    rule.addTarget(new targets.LambdaFunction(this.oddsCollectorFunction));
  }
}
