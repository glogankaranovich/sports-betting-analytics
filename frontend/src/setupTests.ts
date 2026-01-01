// Mock environment variables
process.env.REACT_APP_API_URL = 'https://test-api.example.com/prod';
process.env.REACT_APP_STAGE = 'test';

// Mock AWS Amplify config
jest.mock('./amplifyConfig', () => ({}));
