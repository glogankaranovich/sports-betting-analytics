import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import { InfrastructureStack } from './infrastructure-stack';

export interface SportsBettingStageProps extends cdk.StageProps {
  stage: string;
}

export class SportsBettingStage extends cdk.Stage {
  constructor(scope: Construct, id: string, props: SportsBettingStageProps) {
    super(scope, id, props);

    // Create infrastructure stack
    new InfrastructureStack(this, 'Infrastructure', {
      stage: props.stage,
    });
  }
}
