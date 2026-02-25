import { useState, useCallback, useEffect } from 'react';
import { Message, AnalystResponse } from '../types';
import { analyticsApi } from '../services/api';

const generateId = () => Math.random().toString(36).substring(2, 15);

export function useAnalyst() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string>('');
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Initialize session on mount
  useEffect(() => {
    const initSession = async () => {
      try {
        const { sessionId: newSessionId } = await analyticsApi.createSession();
        setSessionId(newSessionId);

        // Load suggestions
        const suggestionsData = await analyticsApi.getSuggestions();
        setSuggestions(suggestionsData);

        // Add welcome message
        setMessages([{
          id: generateId(),
          role: 'assistant',
          content: `Welcome to Thomson Reuters Content Licensing Analytics! I can help you analyze:

• **Revenue Data** - Total revenue, by country, industry, or media type
• **Customer Insights** - Top customers, account analysis
• **Order Analysis** - Order status, trends over time
• **Content Performance** - Photographers, assets, media types
• **License Contracts** - Usage agreements and contract types

Try asking: *"What is the total revenue?"* or *"Show me the top 10 customers"*`,
          timestamp: new Date(),
        }]);
      } catch (err) {
        setError('Failed to initialize session. Please refresh the page.');
        // Still show welcome message even if session fails
        setMessages([{
          id: generateId(),
          role: 'assistant',
          content: 'Welcome! There was an issue connecting to the server. Please check that the backend is running.',
          timestamp: new Date(),
        }]);
      }
    };

    initSession();
  }, []);

  const sendQuery = useCallback(async (question: string) => {
    if (!question.trim() || isLoading) return;

    const userMessage: Message = {
      id: generateId(),
      role: 'user',
      content: question,
      timestamp: new Date(),
    };

    // Add user message and loading indicator
    const loadingMessage: Message = {
      id: generateId(),
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isLoading: true,
    };

    setMessages(prev => [...prev, userMessage, loadingMessage]);
    setIsLoading(true);
    setError(null);

    try {
      // Build conversation history for context
      const conversationHistory = messages
        .filter(m => !m.isLoading)
        .slice(-10) // Last 10 messages for context
        .map(m => ({
          role: m.role,
          content: m.content,
        }));

      const response: AnalystResponse = await analyticsApi.query(
        question,
        sessionId,
        conversationHistory
      );

      const assistantMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        data: response.data,
        sql: response.sql,
      };

      // Replace loading message with actual response
      setMessages(prev => [
        ...prev.slice(0, -1),
        assistantMessage,
      ]);

      // Update suggestions if provided
      if (response.suggestions) {
        setSuggestions(response.suggestions);
      }
    } catch (err: any) {
      const errorMessage: Message = {
        id: generateId(),
        role: 'assistant',
        content: `I encountered an error: ${err.message || 'Unknown error'}. Please check that the backend server is running and try again.`,
        timestamp: new Date(),
      };

      setMessages(prev => [...prev.slice(0, -1), errorMessage]);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  }, [messages, sessionId, isLoading]);

  const clearConversation = useCallback(() => {
    setMessages([{
      id: generateId(),
      role: 'assistant',
      content: 'Conversation cleared. How can I help you analyze the content licensing data?',
      timestamp: new Date(),
    }]);
  }, []);

  const exportData = useCallback(async (data: any[], format: 'csv' | 'json') => {
    try {
      const blob = await analyticsApi.exportResults(data, format);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `tr-analytics-export.${format}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);
    } catch (err: any) {
      setError(`Export failed: ${err.message}`);
    }
  }, []);

  return {
    messages,
    isLoading,
    suggestions,
    error,
    sendQuery,
    clearConversation,
    exportData,
  };
}
