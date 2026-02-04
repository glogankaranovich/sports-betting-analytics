import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'https://lpykx3ka6a.execute-api.us-east-1.amazonaws.com/prod';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface AIAgentProps {
  token: string;
}

export const AIAgent: React.FC<AIAgentProps> = ({ token }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: 'Hi! I\'m your AI betting analyst. I can help you:\n\n• Create custom betting models\n• Analyze historical performance\n• Explain predictions\n• Optimize model parameters\n\nWhat would you like to do?',
      timestamp: new Date()
    }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post(
        `${API_URL}/ai-agent/chat`,
        {
          message: input,
          conversation_history: messages.slice(-10)
        },
        {
          headers: { Authorization: `Bearer ${token}` }
        }
      );

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage: Message = {
        role: 'assistant',
        content: 'Sorry, I encountered an error. Please try again.',
        timestamp: new Date()
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="ai-agent">
      <div className="chat-header">
        <h2>🤖 AI Betting Analyst</h2>
        <p>Ask me anything about betting models and analytics</p>
      </div>

      <div className="chat-messages">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <div className="message-content">
              {msg.content.split('\n').map((line, i) => (
                <p key={i}>{line}</p>
              ))}
            </div>
            <div className="message-time">
              {msg.timestamp.toLocaleTimeString()}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="typing">
              <span></span><span></span><span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              sendMessage();
            }
          }}
          placeholder="Ask me anything..."
          disabled={loading}
          rows={3}
        />
        <button onClick={sendMessage} disabled={loading || !input.trim()}>
          Send
        </button>
      </div>

      <style>{`
        .ai-agent {
          display: flex;
          flex-direction: column;
          height: calc(100vh - 200px);
          padding: 20px;
        }

        .chat-header {
          text-align: center;
          margin-bottom: 20px;
          padding-bottom: 20px;
          border-bottom: 2px solid rgba(102, 126, 234, 0.3);
        }

        .chat-header h2 {
          margin: 0 0 10px 0;
          color: #667eea;
        }

        .chat-header p {
          margin: 0;
          color: #a0aec0;
          font-size: 14px;
        }

        .chat-messages {
          flex: 1;
          overflow-y: auto;
          padding: 20px;
          background: rgba(255, 255, 255, 0.02);
          border-radius: 12px;
          margin-bottom: 20px;
        }

        .message {
          margin-bottom: 20px;
          display: flex;
          flex-direction: column;
        }

        .message.user {
          align-items: flex-end;
        }

        .message.assistant {
          align-items: flex-start;
        }

        .message-content {
          max-width: 70%;
          padding: 15px 20px;
          border-radius: 12px;
          line-height: 1.6;
        }

        .message.user .message-content {
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          color: white;
        }

        .message.assistant .message-content {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.1);
          color: #e2e8f0;
        }

        .message-content p {
          margin: 0 0 10px 0;
        }

        .message-content p:last-child {
          margin-bottom: 0;
        }

        .message-time {
          font-size: 12px;
          color: #a0aec0;
          margin-top: 5px;
          padding: 0 10px;
        }

        .typing {
          display: flex;
          gap: 5px;
          padding: 15px 20px;
        }

        .typing span {
          width: 8px;
          height: 8px;
          background: #667eea;
          border-radius: 50%;
          animation: typing 1.4s infinite;
        }

        .typing span:nth-child(2) {
          animation-delay: 0.2s;
        }

        .typing span:nth-child(3) {
          animation-delay: 0.4s;
        }

        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
            opacity: 0.5;
          }
          30% {
            transform: translateY(-10px);
            opacity: 1;
          }
        }

        .chat-input {
          display: flex;
          gap: 10px;
          align-items: flex-end;
        }

        .chat-input textarea {
          flex: 1;
          padding: 15px;
          background: rgba(255, 255, 255, 0.05);
          border: 2px solid rgba(255, 255, 255, 0.1);
          border-radius: 12px;
          color: #e2e8f0;
          font-size: 14px;
          resize: none;
          font-family: inherit;
        }

        .chat-input textarea:focus {
          outline: none;
          border-color: #667eea;
        }

        .chat-input button {
          padding: 15px 30px;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          border: none;
          border-radius: 12px;
          color: white;
          font-weight: 600;
          cursor: pointer;
          transition: transform 0.2s;
        }

        .chat-input button:hover:not(:disabled) {
          transform: translateY(-2px);
        }

        .chat-input button:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }
      `}</style>
    </div>
  );
};
