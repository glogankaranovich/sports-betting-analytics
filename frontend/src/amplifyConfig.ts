import { Amplify } from 'aws-amplify';

// Environment-specific Cognito configuration
const getEnvironmentConfig = () => {
  const hostname = window.location.hostname;
  
  if (hostname.includes('beta.')) {
    return {
      userPoolId: 'us-east-1_eXhfQ3HC3',
      userPoolClientId: '62nen1ftj2rk34t10eosvmimfc',
    };
  }
  
  // Default to dev
  return {
    userPoolId: 'us-east-1_UT5jyAP5L',
    userPoolClientId: '4qs12vau007oineekjldjkn6v0',
  };
};

const envConfig = getEnvironmentConfig();

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: envConfig.userPoolId,
      userPoolClientId: envConfig.userPoolClientId,
      loginWith: {
        email: true,
      },
      signUpVerificationMethod: 'code' as const,
      userAttributes: {
        email: {
          required: true,
        },
      },
      allowGuestAccess: false,
      passwordFormat: {
        minLength: 8,
        requireLowercase: true,
        requireUppercase: true,
        requireNumbers: true,
        requireSpecialCharacters: false,
      },
    },
  },
};

// @ts-ignore - Using User Pool only, no Identity Pool needed
Amplify.configure(amplifyConfig);

export default amplifyConfig;
