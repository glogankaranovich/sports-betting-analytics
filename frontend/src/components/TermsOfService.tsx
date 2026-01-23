import React from 'react';
import './LegalPage.css';

const TermsOfService: React.FC = () => {
  return (
    <div className="legal-page">
      <div className="legal-container">
        <h1>Terms of Service</h1>
        <p className="last-updated">Last Updated: January 23, 2026</p>

        <section>
          <h2>1. Acceptance of Terms</h2>
          <p>By accessing or using Carpool Bets ("Service"), you agree to be bound by these Terms of Service. If you do not agree, do not use the Service.</p>
        </section>

        <section>
          <h2>2. Description of Service</h2>
          <p>Carpool Bets provides statistical analysis, data insights, and informational tools related to sporting events.</p>
          <p><strong>We do not operate a sportsbook, do not accept or place bets, and do not facilitate gambling transactions of any kind.</strong></p>
          <p>All content is provided for informational and entertainment purposes only.</p>
        </section>

        <section>
          <h2>3. No Gambling or Betting Advice</h2>
          <p>The Service does not constitute:</p>
          <ul>
            <li>Gambling advice</li>
            <li>Financial advice</li>
            <li>Investment advice</li>
          </ul>
          <p><strong>No guarantees are made regarding accuracy, completeness, or outcomes.</strong> Any decisions made based on information from the Service are made entirely at your own risk.</p>
        </section>

        <section>
          <h2>4. Eligibility</h2>
          <ul>
            <li>You must be at least <strong>21 years old</strong> (or the legal gambling age in your jurisdiction) to use the Service.</li>
            <li>You are responsible for ensuring that your use of the Service complies with all applicable local, state, and federal laws, including gambling laws.</li>
            <li>You must not be located in a jurisdiction where sports betting is prohibited.</li>
          </ul>
        </section>

        <section>
          <h2>5. User Responsibilities</h2>
          <p>You agree not to:</p>
          <ul>
            <li>Use the Service for unlawful purposes</li>
            <li>Misrepresent data or outcomes</li>
            <li>Attempt to reverse engineer or scrape the platform</li>
            <li>Use automated tools without authorization</li>
            <li>Share your account credentials with others</li>
            <li>Violate any applicable gambling laws or regulations</li>
          </ul>
        </section>

        <section>
          <h2>6. Intellectual Property</h2>
          <p>All content, trademarks, algorithms, and design elements are the exclusive property of Carpool Bets and may not be copied or reused without permission.</p>
        </section>

        <section>
          <h2>7. Disclaimer of Warranties</h2>
          <p><strong>The Service is provided "AS IS" and "AS AVAILABLE."</strong></p>
          <p>We disclaim all warranties, express or implied, including accuracy, reliability, or fitness for a particular purpose.</p>
          <p className="warning"><strong>GAMBLING INVOLVES RISK. YOU MAY LOSE MONEY. NEVER BET MORE THAN YOU CAN AFFORD TO LOSE.</strong></p>
        </section>

        <section>
          <h2>8. Limitation of Liability</h2>
          <p>To the fullest extent permitted by law, Carpool Bets shall not be liable for:</p>
          <ul>
            <li>Any losses incurred from betting or wagering</li>
            <li>Indirect, incidental, or consequential damages</li>
            <li>Loss of profits or data</li>
            <li>Any damages arising from use or inability to use the Service</li>
            <li>Third-party content or actions</li>
          </ul>
          <p><strong>IN NO EVENT SHALL OUR TOTAL LIABILITY EXCEED $100 USD.</strong></p>
        </section>

        <section>
          <h2>9. Responsible Gambling</h2>
          <p>We encourage responsible gambling practices:</p>
          <ul>
            <li><strong>National Problem Gambling Helpline</strong>: 1-800-522-4700</li>
            <li><strong>Gamblers Anonymous</strong>: www.gamblersanonymous.org</li>
            <li><strong>National Council on Problem Gambling</strong>: ncpgambling.org</li>
          </ul>
          <p>If you or someone you know has a gambling problem, please seek help immediately.</p>
        </section>

        <section>
          <h2>10. Data and Privacy</h2>
          <p>Your use of the Service is also governed by our <a href="/privacy">Privacy Policy</a>. By using the Service, you consent to our data practices as described in the Privacy Policy.</p>
        </section>

        <section>
          <h2>11. Modifications to Terms</h2>
          <p>We reserve the right to modify these Terms at any time. Continued use of the Service after changes constitutes acceptance of the modified Terms.</p>
        </section>

        <section>
          <h2>12. Termination</h2>
          <p>We may suspend or terminate access to the Service at any time, with or without notice, for any violation of these Terms or for any other reason.</p>
        </section>

        <section>
          <h2>13. Governing Law and Dispute Resolution</h2>
          <p>These Terms are governed by the laws of the United States, without regard to conflict of law principles.</p>
          <p>Any disputes shall be resolved through binding arbitration in accordance with the rules of the American Arbitration Association.</p>
        </section>

        <section>
          <h2>14. Severability</h2>
          <p>If any provision of these Terms is found to be unenforceable, the remaining provisions shall remain in full force and effect.</p>
        </section>

        <section>
          <h2>15. Entire Agreement</h2>
          <p>These Terms, together with the Privacy Policy, constitute the entire agreement between you and Carpool Bets regarding the Service.</p>
        </section>

        <div className="disclaimer-box">
          <p><strong>IMPORTANT DISCLAIMER</strong>: This Service provides analysis and information only. We are not responsible for any betting decisions or financial losses. Gambling involves risk and may be addictive. Please gamble responsibly.</p>
        </div>
      </div>
    </div>
  );
};

export default TermsOfService;
