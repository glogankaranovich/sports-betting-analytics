#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as ec2 from 'aws-cdk-lib/aws-ec2';
import * as ecs from 'aws-cdk-lib/aws-ecs';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export interface EcsClusterStackProps extends cdk.StackProps {
  stage: string;
}

export class EcsClusterStack extends cdk.Stack {
  public readonly cluster: ecs.Cluster;
  public readonly vpc: ec2.IVpc;

  constructor(scope: Construct, id: string, props: EcsClusterStackProps) {
    super(scope, id, props);

    // Use default VPC with public subnets
    this.vpc = ec2.Vpc.fromLookup(this, 'DefaultVpc', {
      isDefault: true,
    });

    // Create ECS cluster
    this.cluster = new ecs.Cluster(this, 'BatchCluster', {
      clusterName: `${props.stage}-batch-processing`,
      vpc: this.vpc,
      enableFargateCapacityProviders: true,
    });

    // Output cluster name
    new cdk.CfnOutput(this, 'ClusterName', {
      value: this.cluster.clusterName,
      exportName: `${props.stage}-BatchClusterName`,
    });

    new cdk.CfnOutput(this, 'ClusterArn', {
      value: this.cluster.clusterArn,
      exportName: `${props.stage}-BatchClusterArn`,
    });
  }
}
