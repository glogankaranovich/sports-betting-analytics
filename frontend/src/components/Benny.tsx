import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'https://ddzbfblwr0.execute-api.us-east-1.amazonaws.com/prod';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

interface BennyProps {
  userId: string;
  token: string;
  isFullPage?: boolean;
  subscription?: any;
}

export const Benny: React.FC<BennyProps> = ({ userId, token, isFullPage = false, subscription }) => {
  const hasAccess = subscription?.limits?.benny_ai !== false;
  const canCreateModels = subscription?.limits?.user_models !== false;
  
  const getWelcomeMessage = () => {
    const features = [
      'Analyze prediction performance',
      'Query historical stats',
      'Explain predictions'
    ];
    
    if (canCreateModels) {
      features.unshift('Create custom betting models');
    }
    
    return `Hey! I'm Benny, your AI betting analyst. I can help you:\n\n${features.map(f => `• ${f}`).join('\n')}\n\nWhat would you like to do?`;
  };

  const [isOpen, setIsOpen] = useState(isFullPage);
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: getWelcomeMessage()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isOpen) {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, isOpen]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const conversationHistory = messages.map(m => ({
        role: m.role,
        content: m.content
      }));

      const response = await axios.post(
        `${API_URL}/ai-agent/chat`,
        {
          message: input,
          user_id: userId,
          conversation_history: conversationHistory.slice(-10)
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      let responseText = response.data.response;
      if (typeof responseText === 'object' && responseText.content) {
        if (Array.isArray(responseText.content)) {
          responseText = responseText.content
            .filter((c: any) => c.type === 'text')
            .map((c: any) => c.text)
            .join('\n');
        }
      }

      const assistantMessage: Message = {
        role: 'assistant',
        content: responseText
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.'
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {/* Floating Chat Button - hide in full page mode */}
      {!isFullPage && (
        <button
          className="benny-button"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Chat with Benny"
        >
          {isOpen ? '✕' : '🤖'}
        </button>
      )}

      {/* Chat Window */}
      {isOpen && !hasAccess && (
        <div className={`benny-chat ${isFullPage ? 'full-page' : ''}`}>
          <div className="benny-upgrade-prompt">
            <h3>🤖 Benny AI</h3>
            <p>Get AI-powered betting insights and analysis with Benny.</p>
            <ul>
              <li>Analyze prediction performance</li>
              <li>Query historical stats</li>
              <li>Explain predictions</li>
              <li>Get personalized recommendations</li>
            </ul>
            <button className="upgrade-button">Upgrade to Access Benny</button>
          </div>
        </div>
      )}

      {isOpen && hasAccess && (
        <div className={`benny-chat ${isFullPage ? 'full-page' : ''}`}>
          <div className="benny-header">
            <div>
              <h3>🤖 Benny</h3>
              <p>Your AI Betting Analyst</p>
            </div>
            {!isFullPage && <button onClick={() => setIsOpen(false)}>✕</button>}
          </div>

          <div className="benny-messages">
            {messages.map((msg, idx) => (
              <div key={idx} className={`benny-message ${msg.role}`}>
                <div className="benny-message-content">
                  {msg.content.split('\n').map((line, i) => (
                    <p key={i}>{line}</p>
                  ))}
                </div>
              </div>
            ))}
            {loading && (
              <div className="benny-message assistant">
                <div className="benny-typing">
                  <span></span><span></span><span></span>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          <div className="benny-input">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
              placeholder="Ask Benny anything..."
              disabled={loading}
              rows={2}
            />
            <button onClick={sendMessage} disabled={loading || !input.trim()}>
              Send
            </button>
          </div>
        </div>
      )}

      <style>{`
        .benny-upgrade-prompt {
          padding: 3rem 2rem;
          text-align: center;
          color: rgba(255, 255, 255, 0.9);
        }

        .benny-upgrade-prompt h3 {
          font-size: 2rem;
          margin-bottom: 1rem;
          color: #fff;
        }

        .benny-upgrade-prompt p {
          font-size: 1.1rem;
          margin-bottom: 2rem;
          color: rgba(255, 255, 255, 0.8);
        }

        .benny-upgrade-prompt ul {
          list-style: none;
          padding: 0;
          margin: 2rem 0;
          text-align: left;
          max-width: 400px;
          margin-left: auto;
          margin-right: auto;
        }

        .benny-upgrade-prompt li {
          padding: 0.75rem 0;
          padding-left: 2rem;
          position: relative;
          color: rgba(255, 255, 255, 0.9);
        }

        .benny-upgrade-prompt li:before {
          content: '✓';
          position: absolute;
          left: 0;
          color: #48bb78;
          font-weight: bold;
        }

        .upgrade-button {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
          border: none;
          padding: 1rem 2rem;
          font-size: 1.1rem;
          font-weight: 600;
          border-radius: 8px;
          cursor: pointer;
          transition: transform 0.2s, box-shadow 0.2s;
          margin-top: 1rem;
        }

        .upgrade-button:hover {
          transform: translateY(-2px);
          box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        }

        .benny-button {
          position: fixed;
          bottom: 60px;
          right: 30px;
          width: 60px;
          height: 60px;
          border-radius: 50%;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border: none;
          color: white;
          font-size: 28px;
          cursor: pointer;
          box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
          transition: transform 0.2s, box-shadow 0.2s;
          z-index: 1000;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .benny-button:hover {
          transform: scale(1.1);
          box-shadow: 0 6px 25px rgba(102, 126, 234, 0.6);
        }

        .benny-chat {
          position: fixed;
          bottom: 100px;
          right: 30px;
          width: 400px;
          height: 600px;
          background: rgba(26, 32, 44, 0.98);
          border: 2px solid rgba(102, 126, 234, 0.3);
          border-radius: 16px;
          box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
          display: flex;
          flex-direction: column;
          z-index: 1000;
          backdrop-filter: blur(10px);
        }

        .benny-chat.full-page {
          position: relative;
          bottom: auto;
          right: auto;
          width: 100%;
          max-width: 1200px;
          height: calc(100vh - 200px);
          margin: 0 auto;
          border-radius: 12px;
        }

        .benny-header {
          padding: 20px;
          border-bottom: 2px solid rgba(102, 126, 234, 0.3);
          display: flex;
          justify-content: space-between;
          align-items: center;
        }

        .benny-header h3 {
          margin: 0;
          color: #667eea;
          font-size: 18px;
        }

        .benny-header p {
          margin: 5px 0 0 0;
          color: #a0aec0;
          font-size: 12px;
        }

        .benny-header button {
          background: none;
          border: none;
          color: #a0aec0;
          font-size: 24px;
          cursor: pointer;
          padding: 0;
          width: 30px;
          height: 30px;
          display: flex;
          align-items: center;
          justify-content: center;
          transition: color 0.2s;
        }

        .benny-header button:hover {
          color: #e2e8f0;
        }

        .benny-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
        }

        .benny-message {
          margin-bottom: 15px;
          display: flex;
          flex-direction: column;
        }

        .benny-message.user {
          align-items: flex-end;
        }

        .benny-message.assistant {
          align-items: flex-start;
        }

        .benny-message-content {
          max-width: 85%;
          padding: 12px 16px;
          border-radius: 12px;
          line-height: 1.5;
          font-size: 14px;
        }

        .benny-message.user .benny-message-content {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }

        .benny-message.assistant .benny-message-content {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #e2e8f0;
        }

        .benny-message-content p {
          margin: 0 0 8px 0;
        }

        .benny-message-content p:last-child {
          margin-bottom: 0;
        }

        .benny-typing {
          display: flex;
          gap: 5px;
          padding: 12px 16px;
        }

        .benny-typing span {
          width: 8px;
          height: 8px;
          background: #667eea;
          border-radius: 50%;
          animation: benny-typing 1.4s infinite;
        }

        .benny-typing span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .benny-typing span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes benny-typing {
          0%, 60%, 100% {
            transform: translateY(0);
            opacity: 0.5;
          }
          30% {
            transform: translateY(-8px);
            opacity: 1;
          }
        }

        .benny-input {
          padding: 15px;
          border-top: 2px solid rgba(102, 126, 234, 0.3);
          display: flex;
          gap: 10px;
        }

        .benny-input textarea {
          flex: 1;
          padding: 10px;
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          border-radius: 8px;
          color: #e2e8f0;
          font-size: 14px;
          resize: none;
          font-family: inherit;
        }

        .benny-input textarea:focus {
          outline: none;
          border-color: #667eea;
        }

        .benny-input button {
          padding: 10px 20px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border: none;
          border-radius: 8px;
          color: white;
          font-weight: 600;
          cursor: pointer;
          font-size: 14px;
          transition: transform 0.2s;
        }

        .benny-input button:hover:not(:disabled) {
          transform: translateY(-2px);
        }

        .benny-input button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        @media (max-width: 768px) {
          .benny-chat {
            width: calc(100vw - 40px);
            height: calc(100vh - 140px);
            right: 20px;
            bottom: 90px;
          }

          .benny-button {
            right: 20px;
            bottom: 20px;
          }
        }
      `}</style>
    </>
  );
};
