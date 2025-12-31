import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import { Construct } from 'constructs';

export interface MinimalStackProps extends cdk.StackProps {
  stage: string;
}

export class MinimalStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: MinimalStackProps) {
    super(scope, id, props);

    // Just create a simple DynamoDB table
    const betsTable = new dynamodb.Table(this, 'BetsTable', {
      tableName: `sports-betting-bets-${props.stage}`,
      partitionKey: { name: 'bet_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: props.stage === 'prod' ? cdk.RemovalPolicy.RETAIN : cdk.RemovalPolicy.DESTROY,
    });
  }
}
