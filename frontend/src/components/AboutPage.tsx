import React from 'react';
import './AboutPage.css';

const getEmailDomain = () => {
  const stage = process.env.REACT_APP_STAGE;
  return stage === 'prod' ? 'carpoolbets.com' : `${stage}.carpoolbets.com`;
};

export const AboutPage: React.FC = () => {
  const domain = getEmailDomain();
  
  return (
    <div className="about-page">
      <section className="about-section">
        <h2>About Carpool Bets</h2>
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
      
      <section className="about-section">
        <h2>Features</h2>
        <div className="features-grid">
          <div className="feature-card">
            <div className="feature-icon">🤖</div>
            <h3>AI Assistant (Benny)</h3>
            <p>Natural language interface powered by Claude AI for creating custom betting models and analyzing predictions.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📊</div>
            <h3>Custom Models</h3>
            <p>Build personalized betting models with configurable data sources and weighting strategies.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">📈</div>
            <h3>Real-Time Analytics</h3>
            <p>Live odds tracking, team statistics, player props, and performance metrics.</p>
          </div>
          <div className="feature-card">
            <div className="feature-icon">🎲</div>
            <h3>Prediction Engine</h3>
            <p>Advanced ML models analyzing historical data, recent form, injuries, and betting trends.</p>
          </div>
        </div>
      </section>
      
      <section className="about-section">
        <h2>Technology</h2>
        <p>
          Our platform is built on AWS cloud infrastructure, utilizing services including Lambda, DynamoDB, 
          API Gateway, and Bedrock AI. We integrate with The Odds API for real-time betting data and employ 
          machine learning models for prediction generation.
        </p>
      </section>
      
      <section className="about-section">
        <h2>Contact</h2>
        <div className="contact-grid">
          <div className="contact-item">
            <strong>General Inquiries</strong>
            <a href={`mailto:info@${domain}`}>info@{domain}</a>
          </div>
          <div className="contact-item">
            <strong>Customer Support</strong>
            <a href={`mailto:support@${domain}`}>support@{domain}</a>
          </div>
          <div className="contact-item">
            <strong>Security Issues</strong>
            <a href={`mailto:security@${domain}`}>security@{domain}</a>
          </div>
          <div className="contact-item">
            <strong>Compliance & Responsible Gambling</strong>
            <a href={`mailto:compliance@${domain}`}>compliance@{domain}</a>
          </div>
        </div>
      </section>
      
      <div className="disclaimer-box">
        <strong>⚠️ Disclaimer:</strong> This platform provides betting analysis for entertainment and educational 
        purposes only. All predictions are informational and do not guarantee profits. Users assume all financial 
        risk. Gambling can be addictive - please gamble responsibly. Must be 21+ to use this service.
        <p style={{ marginTop: '1rem' }}>Problem Gambling Helpline: 1-800-522-4700</p>
      </div>
    </div>
  );
};
