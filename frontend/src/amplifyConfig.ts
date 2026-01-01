import { Amplify } from 'aws-amplify';

const amplifyConfig = {
  Auth: {
    Cognito: {
      userPoolId: 'us-east-1_w5USY1BCN',
      userPoolClientId: '69tqcedjqmee1jr07e6uj17qum',
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
