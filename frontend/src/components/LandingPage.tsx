import React from 'react';
import logo from '../assets/logo_2.png';
import './LandingPage.css';

const LandingPage: React.FC = () => {
  return (
    <div className="landing-page">
      <div className="landing-container">
        <header className="landing-header">
          <img src={logo} alt="Carpool Bets" className="landing-logo" />
          <p className="tagline">AI-Powered Sports Betting Analytics Platform</p>
        </header>
        
        <div className="landing-content">
          <section className="section">
            <h2>About Us</h2>
            <p>
              Carpool Bets is an innovative sports betting analytics platform that leverages artificial intelligence 
              to help users make informed betting decisions. Our platform combines advanced machine learning models, 
              real-time data analysis, and natural language AI assistance to provide comprehensive betting insights.
            </p>
            <p>
              We analyze team statistics, player performance, historical trends, and betting odds to generate 
              data-driven predictions across multiple sports including NBA, NFL, MLB, NHL, and EPL.
            </p>
          </section>
          
          <section className="section">
            <h2>Features</h2>
            <div className="features">
              <div className="feature">
                <h3>🤖 AI Assistant (Benny)</h3>
                <p>Natural language interface powered by Claude AI for creating custom betting models and analyzing predictions.</p>
              </div>
              <div className="feature">
                <h3>📊 Custom Models</h3>
                <p>Build personalized betting models with configurable data sources and weighting strategies.</p>
              </div>
              <div className="feature">
                <h3>📈 Real-Time Analytics</h3>
                <p>Live odds tracking, team statistics, player props, and performance metrics.</p>
              </div>
              <div className="feature">
                <h3>🎲 Prediction Engine</h3>
                <p>Advanced ML models analyzing historical data, recent form, injuries, and betting trends.</p>
              </div>
            </div>
          </section>
          
          <section className="section">
            <h2>Technology</h2>
            <p>
              Our platform is built on AWS cloud infrastructure, utilizing services including Lambda, DynamoDB, 
              API Gateway, and Bedrock AI. We integrate with The Odds API for real-time betting data and employ 
              machine learning models for prediction generation.
            </p>
          </section>
          
          <section className="section">
            <h2>Contact</h2>
            <div className="contact">
              <p><strong>General Inquiries:</strong> <a href="mailto:info@carpoolbets.com">info@carpoolbets.com</a></p>
              <p><strong>Customer Support:</strong> <a href="mailto:support@carpoolbets.com">support@carpoolbets.com</a></p>
              <p><strong>Security Issues:</strong> <a href="mailto:security@carpoolbets.com">security@carpoolbets.com</a></p>
              <p><strong>Compliance & Responsible Gambling:</strong> <a href="mailto:compliance@carpoolbets.com">compliance@carpoolbets.com</a></p>
            </div>
          </section>
          
          <div className="cta-section">
            <a href="/app" className="cta-button">Launch App →</a>
          </div>
          
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
