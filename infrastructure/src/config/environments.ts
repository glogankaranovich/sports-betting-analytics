export interface EnvironmentConfig {
  account: string;
  region: string;
  stage: string;
}

export const ENVIRONMENTS: Record<string, EnvironmentConfig> = {
  dev: {
    account: '540477485595',
    region: 'us-east-1',
    stage: 'dev',
  },
  staging: {
    account: '352312075009',
    region: 'us-east-1',
    stage: 'staging',
  },
  prod: {
    account: '198784968537',
    region: 'us-east-1',
    stage: 'prod',
  },
  pipeline: {
    account: '083314012659',
    region: 'us-east-1',
    stage: 'pipeline',
  },
};
