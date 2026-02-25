import axios from 'axios';
import { AnalystResponse, ConversationContext } from '../types';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 60000,
});

export const analyticsApi = {
  async query(
    question: string,
    sessionId: string,
    conversationHistory?: { role: string; content: string }[]
  ): Promise<AnalystResponse> {
    const response = await apiClient.post('/analyst/query', {
      question,
      sessionId,
      conversationHistory,
    });
    return response.data;
  },

  async getSuggestions(): Promise<string[]> {
    const response = await apiClient.get('/analyst/suggestions');
    return response.data.suggestions;
  },

  async createSession(): Promise<{ sessionId: string }> {
    const response = await apiClient.post('/analyst/session');
    return response.data;
  },

  async getHistory(sessionId: string): Promise<ConversationContext> {
    const response = await apiClient.get(`/analyst/session/${sessionId}/history`);
    return response.data;
  },

  async exportResults(data: any[], format: 'csv' | 'json'): Promise<Blob> {
    const response = await apiClient.post(
      '/analyst/export',
      { data, format },
      { responseType: 'blob' }
    );
    return response.data;
  },

  async healthCheck(): Promise<{ status: string; snowflakeConnected: boolean }> {
    const response = await apiClient.get('/health');
    return response.data;
  },
};

export default analyticsApi;
