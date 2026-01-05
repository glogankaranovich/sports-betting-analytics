import React, { useState } from 'react';
import './AgeVerification.css';

interface AgeVerificationProps {
  onVerified: (isVerified: boolean) => void;
}

const AgeVerification: React.FC<AgeVerificationProps> = ({ onVerified }) => {
  const [birthDate, setBirthDate] = useState('');
  const [error, setError] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!birthDate) {
      setError('Please enter your birth date');
      return;
    }

    const birth = new Date(birthDate);
    const today = new Date();
    const age = today.getFullYear() - birth.getFullYear();
    const monthDiff = today.getMonth() - birth.getMonth();
    
    const actualAge = monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate()) 
      ? age - 1 
      : age;

    if (actualAge >= 21) {
      localStorage.setItem('ageVerified', JSON.stringify({
        verified: true,
        timestamp: new Date().toISOString(),
        age: actualAge
      }));
      onVerified(true);
    } else {
      setError('You must be 21 or older to access this site');
      onVerified(false);
    }
  };

  return (
    <div className="age-verification-overlay">
      <div className="age-verification-modal">
        <div className="age-verification-header">
          <h2>Age Verification Required</h2>
          <p>You must be 21 or older to access this betting analysis platform</p>
        </div>
        
        <form onSubmit={handleSubmit} className="age-verification-form">
          <div className="form-group">
            <label htmlFor="birthDate">Enter your birth date:</label>
            <input
              type="date"
              id="birthDate"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              max={new Date().toISOString().split('T')[0]}
              required
            />
          </div>
          
          {error && <div className="error-message">{error}</div>}
          
          <button type="submit" className="verify-button">
            Verify Age
          </button>
        </form>
        
        <div className="age-verification-footer">
          <p className="disclaimer">
            By proceeding, you confirm that you are of legal gambling age in your jurisdiction 
            and agree to our terms of service.
          </p>
        </div>
      </div>
    </div>
  );
};

export default AgeVerification;
