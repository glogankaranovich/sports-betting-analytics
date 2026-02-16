import React from 'react';
import logo from '../assets/logo_2.png';
import './LandingPage.css';

const getEmailDomain = () => {
  const stage = process.env.REACT_APP_STAGE;
  return stage === 'prod' ? 'carpoolbets.com' : `${stage}.carpoolbets.com`;
};

const LandingPage: React.FC = () => {
  const domain = getEmailDomain();
  
  return (
    <div className="landing-page">
      <div className="landing-container">
        <header className="landing-header">
          <img src={logo} alt="Carpool Bets" className="landing-logo" />
          <p className="tagline">AI-Powered Sports Betting Analytics</p>
        </header>
        
        <div className="landing-content">
          <section className="section">
            <h2>About Carpool Bets</h2>
            <p>
              Carpool Bets is a cutting-edge sports betting analytics platform that combines artificial intelligence, 
              machine learning, and real-time data to help you make smarter betting decisions. We analyze thousands 
              of data points across multiple sports to deliver actionable insights and predictions.
            </p>
          </section>
          
          <section className="section">
            <h2>Key Features</h2>
            <div className="features">
              <div className="feature">
                <h3>🎯 10 Expert Models</h3>
                <p>Access specialized prediction models including Consensus, Value, Momentum, Contrarian, and more. Each model uses unique strategies to analyze games and props.</p>
              </div>
              <div className="feature">
                <h3>🤖 Benny AI Assistant</h3>
                <p>Chat with our AI assistant powered by Claude to get personalized betting insights, model explanations, and strategy recommendations.</p>
              </div>
              <div className="feature">
                <h3>📊 Custom Models</h3>
                <p>Build your own betting models with custom data sources, weighting strategies, and backtesting capabilities.</p>
              </div>
              <div className="feature">
                <h3>📈 Real-Time Analytics</h3>
                <p>Live odds tracking from major sportsbooks, team statistics, player props, injury reports, and performance metrics.</p>
              </div>
              <div className="feature">
                <h3>🏆 Model Comparison</h3>
                <p>Compare model performance, accuracy rates, and ROI across different sports and bet types to find the best strategies.</p>
              </div>
              <div className="feature">
                <h3>🎲 Multi-Sport Coverage</h3>
                <p>Comprehensive analysis for NBA, NFL, MLB, NHL, and EPL with both game predictions and player props.</p>
              </div>
            </div>
          </section>

          <section className="section">
            <h2>Subscription Tiers</h2>
            <div className="features">
              <div className="feature">
                <h3>🆓 Free Tier</h3>
                <p>Access to Ensemble model predictions with basic analysis. Perfect for getting started.</p>
              </div>
              <div className="feature">
                <h3>⭐ Basic - $9.99/mo</h3>
                <p>All 10 system models, detailed reasoning, model comparison, and create up to 3 custom models.</p>
              </div>
              <div className="feature">
                <h3>💎 Pro - $29.99/mo</h3>
                <p>Everything in Basic plus Benny AI assistant, model marketplace, and up to 20 custom models.</p>
              </div>
            </div>
          </section>
          
          <section className="section">
            <h2>Contact Us</h2>
            <div className="contact">
              <p><strong>General Inquiries:</strong> <a href={`mailto:info@${domain}`}>info@{domain}</a></p>
              <p><strong>Customer Support:</strong> <a href={`mailto:support@${domain}`}>support@{domain}</a></p>
              <p><strong>Security Issues:</strong> <a href={`mailto:security@${domain}`}>security@{domain}</a></p>
              <p><strong>Compliance & Responsible Gambling:</strong> <a href={`mailto:compliance@${domain}`}>compliance@{domain}</a></p>
            </div>
          </section>
          
          <div className="disclaimer">
            <strong>⚠️ Disclaimer:</strong> This platform provides betting analysis for entertainment and educational 
            purposes only. All predictions are informational and do not guarantee profits. Users assume all financial 
            risk. Gambling can be addictive - please gamble responsibly. Must be 21+ to use this service.
          </div>
        </div>
        
        <footer className="landing-footer">
          <p>&copy; 2026 Carpool Bets. All rights reserved.</p>
          <p>Problem Gambling Helpline: 1-800-522-4700</p>
        </footer>
      </div>
    </div>
  );
};

export default LandingPage;
