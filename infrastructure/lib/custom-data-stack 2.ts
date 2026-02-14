import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import { Construct } from 'constructs';

export interface CustomDataStackProps extends cdk.StackProps {
  environment: string;
}

export class CustomDataStack extends cdk.Stack {
  public readonly customDataTable: dynamodb.Table;
  public readonly customDataBucket: s3.Bucket;

  constructor(scope: Construct, id: string, props: CustomDataStackProps) {
    super(scope, id, props);

    // Custom Data Table
    this.customDataTable = new dynamodb.Table(this, 'CustomDataTable', {
      tableName: `${id}-CustomData`,
      partitionKey: { name: 'PK', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'SK', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
      pointInTimeRecovery: true,
    });

    // S3 Bucket for custom data files
    this.customDataBucket = new s3.Bucket(this, 'CustomDataBucket', {
      bucketName: `${props.environment}-custom-data-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      versioned: true,
      lifecycleRules: [
        {
          expiration: cdk.Duration.days(90),
        },
      ],
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });
  }
}
