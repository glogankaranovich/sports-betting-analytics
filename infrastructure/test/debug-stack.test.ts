import * as cdk from 'aws-cdk-lib';
import * as Infrastructure from '../lib/infrastructure-stack';

describe('Debug Infrastructure Stack', () => {
  test('Can create stack instance', () => {
    console.log('Creating CDK App...');
    const app = new cdk.App();
    console.log('CDK App created');
    
    console.log('Creating Infrastructure Stack...');
    const stack = new Infrastructure.InfrastructureStack(app, 'DebugStack', {
      stage: 'test'
    });
    console.log('Infrastructure Stack created');
    
    expect(stack).toBeDefined();
  });
});
