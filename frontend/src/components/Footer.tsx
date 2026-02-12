import React from 'react';
import './Footer.css';

const Footer: React.FC = () => {
  return (
    <footer className="app-footer">
      <div className="footer-content">
        <div className="footer-copyright">
          <p>&copy; 2026 Carpool Bets. All rights reserved.</p>
        </div>
        
        <div className="footer-links">
          <a href="/about">About</a>
          <span className="link-separator">•</span>
          <a href="/terms">Terms of Service</a>
          <span className="link-separator">•</span>
          <a href="/privacy">Privacy Policy</a>
          <span className="link-separator">•</span>
          <a href="/responsible-gambling">Responsible Gambling Resources</a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
