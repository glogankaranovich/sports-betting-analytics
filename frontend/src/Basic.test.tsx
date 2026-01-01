import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';

// Simple component test
describe('Frontend Tests', () => {
  test('basic rendering works', () => {
    render(<div>Test Component</div>);
    expect(screen.getByText('Test Component')).toBeInTheDocument();
  });

  test('environment variables are set', () => {
    expect(process.env.REACT_APP_API_URL).toBeDefined();
    expect(process.env.REACT_APP_STAGE).toBeDefined();
  });
});
