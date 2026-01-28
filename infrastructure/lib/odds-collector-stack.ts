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

    // Note: EventBridge schedules are created in sport-specific schedule stacks
    // to avoid hitting CloudFormation's 500 resource limit per stack
  }
}
