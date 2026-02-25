import React, { useRef, useEffect } from 'react';
import { Database, Trash2 } from 'lucide-react';
import { useAnalyst } from './hooks/useAnalyst';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import './styles/App.css';

const App: React.FC = () => {
  const {
    messages,
    isLoading,
    suggestions,
    sendQuery,
    clearConversation,
    exportData,
  } = useAnalyst();

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-title">
          <Database size={24} color="#fa6400" />
          <h1>TR Content Licensing Analytics</h1>
        </div>
        <div className="header-actions">
          <button className="btn btn-secondary" onClick={clearConversation}>
            <Trash2 size={16} />
            Clear
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {/* Chat Container */}
        <div className="chat-container">
          <div className="messages-container">
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                onExport={exportData}
              />
            ))}
            <div ref={messagesEndRef} />
          </div>

          <ChatInput
            onSend={sendQuery}
            isLoading={isLoading}
            suggestions={suggestions}
          />
        </div>
      </main>
    </div>
  );
};

export default App;
