import React from 'react';
import './Footer.css';

const Footer: React.FC = () => {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-section">
          <h4>Legal</h4>
          <ul>
            <li><a href="/terms">Terms of Service</a></li>
            <li><a href="/privacy">Privacy Policy</a></li>
            <li><a href="/responsible-gambling">Responsible Gambling</a></li>
          </ul>
        </div>
        
        <div className="footer-section">
          <h4>Get Help</h4>
          <div className="help-info">
            <p><strong>Problem Gambling Helpline</strong></p>
            <p className="helpline-number">1-800-522-4700</p>
            <p className="help-description">24/7 confidential support</p>
          </div>
        </div>
        
        <div className="footer-section">
          <h4>Resources</h4>
          <ul>
            <li><a href="https://www.ncpgambling.org" target="_blank" rel="noopener noreferrer">NCPG</a></li>
            <li><a href="https://www.gamblersanonymous.org" target="_blank" rel="noopener noreferrer">Gamblers Anonymous</a></li>
            <li><a href="https://www.responsiblegambling.org" target="_blank" rel="noopener noreferrer">RG Council</a></li>
          </ul>
        </div>
      </div>
      
      <div className="footer-bottom">
        <div className="footer-disclaimer">
          <p>
            <strong>Disclaimer:</strong> This platform provides betting analysis for entertainment/educational purposes only. 
            All analysis items are informational and do not guarantee profits. Users assume all financial risk. 
            Gambling can be addictive - please gamble responsibly.
          </p>
        </div>
        
        <div className="footer-copyright">
          <p>&copy; 2026 Carpool Bets. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
