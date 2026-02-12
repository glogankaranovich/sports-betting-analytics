import React from 'react';
import './ResponsibleGambling.css';

interface ResponsibleGamblingProps {
  isOpen: boolean;
  onClose: () => void;
}

const ResponsibleGambling: React.FC<ResponsibleGamblingProps> = ({ isOpen, onClose }) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay">
      <div className="modal-content responsible-gambling-modal">
        <div className="modal-header">
          <h2>Responsible Gambling</h2>
          <button className="close-button" onClick={onClose}>×</button>
        </div>
        
        <div className="modal-body">
          <div className="warning-section">
            <h3>⚠️ Important Gambling Warnings</h3>
            <ul>
              <li>Gambling can be addictive and harmful</li>
              <li>Never bet more than you can afford to lose</li>
              <li>Set limits on time and money spent gambling</li>
              <li>Don't chase losses with bigger bets</li>
              <li>Gambling is not a way to make money or solve financial problems</li>
            </ul>
          </div>

          <div className="resources-section">
            <h3>Get Help</h3>
            <div className="hotline-info">
              <h4>National Problem Gambling Helpline</h4>
              <p className="hotline-number">1-800-522-4700</p>
            </div>
            
            <div className="resource-links">
              <h4>Additional Resources:</h4>
              <ul>
                <li><a href="https://www.ncpgambling.org" target="_blank" rel="noopener noreferrer">National Council on Problem Gambling</a></li>
                <li><a href="https://www.gamblersanonymous.org" target="_blank" rel="noopener noreferrer">Gamblers Anonymous</a></li>
                <li><a href="https://www.responsiblegambling.org" target="_blank" rel="noopener noreferrer">Responsible Gambling Council</a></li>
              </ul>
            </div>
          </div>

          <div className="self-help-section">
            <h3>Self-Help Tools</h3>
            <p>Consider using these tools to maintain control:</p>
            <ul>
              <li>Set daily, weekly, or monthly spending limits</li>
              <li>Use time limits for gambling sessions</li>
              <li>Take regular breaks from gambling</li>
              <li>Self-exclude from gambling sites if needed</li>
            </ul>
          </div>
        </div>
        
        <div className="modal-footer">
          <button className="primary-button" onClick={onClose}>I Understand</button>
        </div>
      </div>
    </div>
  );
};

export default ResponsibleGambling;
