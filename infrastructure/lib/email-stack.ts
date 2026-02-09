import * as cdk from "aws-cdk-lib";
import * as iam from "aws-cdk-lib/aws-iam";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as ses from "aws-cdk-lib/aws-ses";
import * as sesActions from "aws-cdk-lib/aws-ses-actions";
import { Construct } from "constructs";

interface EmailStackProps extends cdk.StackProps {
  stage: string;
}

export class EmailStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props: EmailStackProps) {
    super(scope, id, props);

    const { stage } = props;

    // Determine domain based on environment
    const domain =
      stage === "prod" ? "carpoolbets.com" : `${stage}.carpoolbets.com`;
    const emailAddresses = [
      `info@${domain}`,
      `support@${domain}`,
      `security@${domain}`,
      `compliance@${domain}`,
      `noreply@${domain}`,
    ];

    // S3 bucket for storing incoming emails
    const emailBucket = new s3.Bucket(this, "EmailBucket", {
      bucketName: `carpoolbets-emails-${stage}-${this.account}`,
      encryption: s3.BucketEncryption.S3_MANAGED,
      lifecycleRules: [
        {
          expiration: cdk.Duration.days(30), // Delete emails after 30 days
        },
      ],
      removalPolicy: cdk.RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });

    // Lambda function to forward emails
    const forwarderLambda = new lambda.Function(this, "EmailForwarder", {
      functionName: `email-forwarder-${stage}`,
      runtime: lambda.Runtime.PYTHON_3_11,
      handler: "email_forwarder.lambda_handler",
      code: lambda.Code.fromAsset("../backend", {
        exclude: ["tests", "*.pyc", "__pycache__", ".pytest_cache"],
      }),
      timeout: cdk.Duration.seconds(30),
      environment: {
        EMAIL_BUCKET: emailBucket.bucketName,
        STAGE: stage,
        DOMAIN: domain,
      },
    });

    // Grant permissions
    emailBucket.grantRead(forwarderLambda);
    forwarderLambda.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["ses:SendRawEmail"],
        resources: ["*"],
      })
    );

    // SES receipt rule set
    const ruleSet = new ses.ReceiptRuleSet(this, "EmailRuleSet", {
      receiptRuleSetName: `carpoolbets-rules-${stage}`,
    });

    // Receipt rule for environment-specific emails
    ruleSet.addRule("ForwardAllEmails", {
      recipients: emailAddresses,
      actions: [
        new sesActions.S3({
          bucket: emailBucket,
        }),
        new sesActions.Lambda({
          function: forwarderLambda,
        }),
      ],
    });

    // Outputs
    new cdk.CfnOutput(this, "EmailBucketName", {
      value: emailBucket.bucketName,
      description: "S3 bucket for incoming emails",
    });

    new cdk.CfnOutput(this, "ForwarderLambdaArn", {
      value: forwarderLambda.functionArn,
      description: "Email forwarder Lambda ARN",
    });

    new cdk.CfnOutput(this, "EmailDomain", {
      value: domain,
      description: "Email domain for this environment",
      exportName: `${stage}-email-domain`,
    });

    new cdk.CfnOutput(this, "EmailAddresses", {
      value: emailAddresses.join(", "),
      description: "Email addresses configured for this environment",
    });
  }
}
