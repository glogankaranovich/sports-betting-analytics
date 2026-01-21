import React, { useState, useEffect } from 'react';
import './DisclaimerBanner.css';

const DisclaimerBanner: React.FC = () => {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem('disclaimer-dismissed');
    if (!dismissed) {
      setIsVisible(true);
    }
  }, []);

  const handleDismiss = () => {
    localStorage.setItem('disclaimer-dismissed', 'true');
    setIsVisible(false);
  };

  if (!isVisible) return null;

  return (
    <div className="disclaimer-banner">
      <div className="disclaimer-content">
        <span className="disclaimer-text">
          ⚠️ <strong>Risk Warning:</strong> All betting analysis items are for entertainment/educational purposes only. 
          Gambling involves risk of loss. Never bet more than you can afford to lose. 
          Must be 21+ to participate.
        </span>
        <button 
          className="disclaimer-close"
          onClick={handleDismiss}
          aria-label="Close disclaimer"
        >
          ×
        </button>
      </div>
    </div>
  );
};

export default DisclaimerBanner;
