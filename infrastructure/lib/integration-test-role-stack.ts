import * as cdk from 'aws-cdk-lib';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface IntegrationTestRoleStackProps extends cdk.StackProps {
  pipelineAccountId: string;
}

export class IntegrationTestRoleStack extends cdk.Stack {
  public readonly roleArn: string;

  constructor(scope: Construct, id: string, props: IntegrationTestRoleStackProps) {
    super(scope, id, props);

    // Create role that can be assumed by the pipeline account
    const integrationTestRole = new iam.Role(this, 'PipelineIntegrationTestRole', {
      roleName: 'PipelineIntegrationTestRole',
      assumedBy: new iam.AccountPrincipal(props.pipelineAccountId),
      description: 'Role for pipeline integration tests to access Lambda and DynamoDB',
      inlinePolicies: {
        IntegrationTestPolicy: new iam.PolicyDocument({
          statements: [
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'lambda:InvokeFunction',
                'lambda:ListFunctions'
              ],
              resources: ['*']
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'dynamodb:Scan',
                'dynamodb:Query',
                'dynamodb:GetItem'
              ],
              resources: ['*']
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'cloudformation:DescribeStacks',
                'cloudformation:ListStacks'
              ],
              resources: ['*']
            }),
            new iam.PolicyStatement({
              effect: iam.Effect.ALLOW,
              actions: [
                'cognito-idp:AdminInitiateAuth',
                'cognito-idp:AdminGetUser'
              ],
              resources: ['*']
            })
          ]
        })
      }
    });

    this.roleArn = integrationTestRole.roleArn;

    // Output the role ARN for reference
    new cdk.CfnOutput(this, 'IntegrationTestRoleArn', {
      value: this.roleArn,
      description: 'ARN of the role for pipeline integration tests'
    });
  }
}
