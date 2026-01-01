import { Amplify } from 'aws-amplify';

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_UT5jyAP5L',
      userPoolClientId: '4qs12vau007oineekjldjkn6v0',
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
