import React from 'react';
import './LegalPage.css';

const PrivacyPolicy: React.FC = () => {
  return (
    <div className="legal-page">
      <div className="legal-container">
        <h1>Privacy Policy</h1>
        <p className="last-updated">Last Updated: January 23, 2026</p>

        <section>
          <h2>1. Information We Collect</h2>
          <p>We may collect:</p>
          
          <h3>Personal Information</h3>
          <ul>
            <li>Email address</li>
            <li>Account credentials</li>
            <li>IP address</li>
            <li>Device and browser data</li>
          </ul>

          <h3>Usage Data</h3>
          <ul>
            <li>Pages visited</li>
            <li>Feature usage</li>
            <li>Interaction timestamps</li>
          </ul>

          <p>We do not collect payment card data unless explicitly stated.</p>
        </section>

        <section>
          <h2>2. How We Use Information</h2>
          <p>We use collected data to:</p>
          <ul>
            <li>Operate and improve the Service</li>
            <li>Provide customer support</li>
            <li>Communicate updates</li>
            <li>Maintain security and prevent fraud</li>
            <li>Comply with legal obligations</li>
          </ul>
        </section>

        <section>
          <h2>3. Legal Bases for Processing (GDPR)</h2>
          <p>We process personal data based on:</p>
          <ul>
            <li>User consent</li>
            <li>Performance of a contract</li>
            <li>Legitimate business interests</li>
            <li>Legal compliance</li>
          </ul>
        </section>

        <section>
          <h2>4. Cookies & Tracking</h2>
          <p>We use cookies and similar technologies for:</p>
          <ul>
            <li>Authentication</li>
            <li>Analytics</li>
            <li>Performance optimization</li>
          </ul>
          <p>You may disable cookies via browser settings.</p>
        </section>

        <section>
          <h2>5. Data Sharing</h2>
          <p><strong>We do not sell personal data.</strong></p>
          <p>We may share data with:</p>
          <ul>
            <li>Service providers (hosting, analytics)</li>
            <li>Legal authorities if required by law</li>
          </ul>
          <p>All vendors are contractually obligated to protect your data.</p>
        </section>

        <section>
          <h2>6. Data Retention</h2>
          <p>We retain personal data only as long as necessary for:</p>
          <ul>
            <li>Service operation</li>
            <li>Legal compliance</li>
            <li>Legitimate business purposes</li>
          </ul>
        </section>

        <section>
          <h2>7. Your Rights</h2>
          
          <h3>GDPR (EU Users):</h3>
          <ul>
            <li>Access your data</li>
            <li>Correct inaccuracies</li>
            <li>Request deletion</li>
            <li>Restrict processing</li>
            <li>Data portability</li>
            <li>Withdraw consent</li>
          </ul>

          <h3>CCPA (California Residents):</h3>
          <ul>
            <li>Know what data is collected</li>
            <li>Request deletion</li>
            <li>Opt out of data sale (we do not sell data)</li>
            <li>Non-discrimination for exercising rights</li>
          </ul>
        </section>

        <section>
          <h2>8. Data Security</h2>
          <p>We implement reasonable administrative, technical, and physical safeguards to protect your data. However, no system is 100% secure.</p>
        </section>

        <section>
          <h2>9. International Transfers</h2>
          <p>If you access the Service outside the U.S., your data may be transferred and processed in the United States in accordance with this Policy.</p>
        </section>

        <section>
          <h2>10. Children's Privacy</h2>
          <p>The Service is not intended for individuals under the age of 21 (or the legal gambling age in your jurisdiction). We do not knowingly collect personal information from minors.</p>
        </section>

        <section>
          <h2>11. Changes to This Policy</h2>
          <p>We may update this Privacy Policy from time to time. Updates will be posted on this page with a revised "Last Updated" date.</p>
        </section>

        <div className="disclaimer-box">
          <p><strong>Note</strong>: This Privacy Policy applies to Carpool Bets and is subject to the <a href="/terms">Terms of Service</a>.</p>
        </div>
      </div>
    </div>
  );
};

export default PrivacyPolicy;
