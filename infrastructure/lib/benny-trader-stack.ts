import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface BennyTraderStackProps extends cdk.StackProps {
  betsTable: dynamodb.ITable;
}

export class BennyTraderStack extends cdk.Stack {
  public readonly bennyTraderFunction: lambda.Function;

  constructor(scope: Construct, id: string, props: BennyTraderStackProps) {
    super(scope, id, props);

    this.bennyTraderFunction = new lambda.Function(this, 'BennyTraderFunction', {
      functionName: `${id}-BennyTrader`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: 'benny_trader_handler.handler',
      code: lambda.Code.fromAsset('../backend', {
        bundling: {
          image: lambda.Runtime.PYTHON_3_11.bundlingImage,
          command: [
            'bash', '-c',
            'pip install -r requirements.txt -t /asset-output && cp -au . /asset-output'
          ],
        },
      }),
      timeout: cdk.Duration.seconds(300),
      memorySize: 1024,
      environment: {
        BETS_TABLE: props.betsTable.tableName,
      },
    });

    props.betsTable.grantReadWriteData(this.bennyTraderFunction);
    
    this.bennyTraderFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['dynamodb:Query'],
      resources: [
        `${props.betsTable.tableArn}/index/*`
      ],
    }));

    new cdk.CfnOutput(this, 'BennyTraderFunctionName', {
      value: this.bennyTraderFunction.functionName,
    });
  }
}
