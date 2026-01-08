import * as cdk from 'aws-cdk-lib';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface AnalysisGeneratorStackProps extends cdk.StackProps {
  environment: string;
  betsTableName: string;
}

export class AnalysisGeneratorStack extends cdk.Stack {
  public readonly analysisGeneratorFunctionArn: cdk.CfnOutput;

  constructor(scope: Construct, id: string, props: AnalysisGeneratorStackProps) {
    super(scope, id, props);

    const analysisGeneratorFunction = new lambda.Function(this, 'AnalysisGeneratorFunction', {
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'analysis_generator.lambda_handler',
      code: lambda.Code.fromAsset('../backend'),
      timeout: cdk.Duration.minutes(15),
      memorySize: 512,
      environment: {
        DYNAMODB_TABLE: props.betsTableName,
        ENVIRONMENT: props.environment
      }
    });

    analysisGeneratorFunction.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:Scan',
        'dynamodb:Query', 
        'dynamodb:GetItem',
        'dynamodb:PutItem',
        'dynamodb:UpdateItem'
      ],
      resources: [
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}`,
        `arn:aws:dynamodb:${this.region}:${this.account}:table/${props.betsTableName}/index/*`
      ]
    }));

    this.analysisGeneratorFunctionArn = new cdk.CfnOutput(this, 'AnalysisGeneratorFunctionArn', {
      value: analysisGeneratorFunction.functionArn
    });
  }
}
