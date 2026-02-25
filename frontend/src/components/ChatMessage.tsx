import React, { useState } from 'react';
import { Message } from '../types';
import { User, Bot, ChevronDown, ChevronUp, Copy, Download } from 'lucide-react';
import DataTable from './DataTable';
import DataChart from './DataChart';

interface ChatMessageProps {
  message: Message;
  onExport?: (data: any[], format: 'csv' | 'json') => void;
}

const ChatMessage: React.FC<ChatMessageProps> = ({ message, onExport }) => {
  const [showSql, setShowSql] = useState(false);
  const [showChart, setShowChart] = useState(true);
  const [copied, setCopied] = useState(false);

  const isUser = message.role === 'user';

  const copySQL = () => {
    if (message.sql) {
      navigator.clipboard.writeText(message.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatContent = (content: string) => {
    // Simple markdown-like formatting
    return content
      .split('\n')
      .map((line, i) => {
        // Bold
        line = line.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
        // Italic
        line = line.replace(/\*(.*?)\*/g, '<em>$1</em>');
        // Bullet points
        if (line.startsWith('• ') || line.startsWith('- ')) {
          return `<li key="${i}">${line.substring(2)}</li>`;
        }
        return line;
      })
      .join('<br/>');
  };

  if (message.isLoading) {
    return (
      <div className={`message message-assistant`}>
        <div className="message-avatar">
          <Bot size={20} color="white" />
        </div>
        <div className="message-content">
          <div className="message-text">
            <div className="loading-indicator">
              <div className="loading-dot"></div>
              <div className="loading-dot"></div>
              <div className="loading-dot"></div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`message message-${message.role}`}>
      <div className="message-avatar">
        {isUser ? (
          <User size={20} color="white" />
        ) : (
          <Bot size={20} color="white" />
        )}
      </div>
      <div className="message-content">
        <div
          className="message-text"
          dangerouslySetInnerHTML={{ __html: formatContent(message.content) }}
        />

        {/* SQL Query Display */}
        {message.sql && (
          <div className="sql-display">
            <div className="sql-header">
              <button
                onClick={() => setShowSql(!showSql)}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'inherit',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.5rem'
                }}
              >
                {showSql ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                Generated SQL
              </button>
              <button
                onClick={copySQL}
                style={{
                  background: 'none',
                  border: 'none',
                  color: 'inherit',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem'
                }}
              >
                <Copy size={14} />
                {copied ? 'Copied!' : 'Copy'}
              </button>
            </div>
            {showSql && (
              <pre className="sql-code">{message.sql}</pre>
            )}
          </div>
        )}

        {/* Data Visualization */}
        {message.data && message.data.rows.length > 0 && (
          <>
            {/* Toggle for chart view */}
            <div style={{
              marginTop: '1rem',
              display: 'flex',
              gap: '0.5rem',
              alignItems: 'center'
            }}>
              <button
                className={`btn btn-secondary ${showChart ? 'active' : ''}`}
                onClick={() => setShowChart(true)}
                style={{ padding: '0.375rem 0.75rem', fontSize: '0.8rem' }}
              >
                Chart
              </button>
              <button
                className={`btn btn-secondary ${!showChart ? 'active' : ''}`}
                onClick={() => setShowChart(false)}
                style={{ padding: '0.375rem 0.75rem', fontSize: '0.8rem' }}
              >
                Table
              </button>
              {onExport && (
                <button
                  className="btn btn-secondary"
                  onClick={() => onExport(message.data!.rows, 'csv')}
                  style={{
                    marginLeft: 'auto',
                    padding: '0.375rem 0.75rem',
                    fontSize: '0.8rem'
                  }}
                >
                  <Download size={14} />
                  Export
                </button>
              )}
            </div>

            {showChart ? (
              <DataChart data={message.data} />
            ) : (
              <DataTable data={message.data} />
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default ChatMessage;
