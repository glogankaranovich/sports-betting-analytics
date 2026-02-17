import React from 'react';
import './LoadingSpinner.css';

const LoadingSpinner: React.FC = () => {
  return (
    <div className="loading-spinner-container">
      <img src="/logo_2.png" alt="Loading" className="loading-spinner-logo" />
    </div>
  );
};

export default LoadingSpinner;
