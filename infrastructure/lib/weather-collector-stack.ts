import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as secretsmanager from 'aws-cdk-lib/aws-secretsmanager';
import { Construct } from 'constructs';
import { getSupportedSportsArray } from './utils/constants';

export interface WeatherCollectorStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
}

export class WeatherCollectorStack extends cdk.Stack {
  public readonly weatherCollectorFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: WeatherCollectorStackProps) {
    super(scope, id, props);

    // Reference weather API secret
    const weatherApiSecret = secretsmanager.Secret.fromSecretNameV2(
      this,
      'WeatherApiSecret',
      `sports-betting/weather-api-key-${props.environment}`
    );

    // Lambda function for weather collection
    this.weatherCollectorFunction = new lambda.Function(this, 'WeatherCollectorFunction', {
      functionName: `weather-collector-${props.environment}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'weather_handler.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(5),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        WEATHER_API_SECRET_ARN: weatherApiSecret.secretArn
      }
    });

    // Grant permissions
    this.weatherCollectorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['dynamodb:Query', 'dynamodb:PutItem', 'dynamodb:GetItem'],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    }));

    weatherApiSecret.grantRead(this.weatherCollectorFunction);

    // EventBridge rules - run every 6 hours (split into groups of 5 due to target limit)
    const sports = getSupportedSportsArray();
    const batchSize = 5;
    
    for (let i = 0; i < sports.length; i += batchSize) {
      const batch = sports.slice(i, i + batchSize);
      const batchNum = Math.floor(i / batchSize) + 1;
      
      const rule = new events.Rule(this, `WeatherCollectorSchedule${batchNum}`, {
        ruleName: `weather-collector-schedule-${props.environment}-${batchNum}`,
        schedule: events.Schedule.rate(cdk.Duration.hours(6)),
        description: `Collect weather data for upcoming games every 6 hours (batch ${batchNum})`
      });
      
      batch.forEach(sport => {
        rule.addTarget(new targets.LambdaFunction(this.weatherCollectorFunction, {
          event: events.RuleTargetInput.fromObject({ sport })
        }));
      });
    }
  }
}
