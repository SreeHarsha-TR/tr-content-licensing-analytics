export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  data?: QueryResult;
  sql?: string;
  isLoading?: boolean;
}

export interface QueryResult {
  columns: string[];
  rows: Record<string, any>[];
  rowCount: number;
  executionTime?: number;
}

export interface ChartData {
  name: string;
  value: number;
  [key: string]: any;
}

export interface ConversationContext {
  sessionId: string;
  messages: Message[];
  currentQuery?: string;
}

export interface AnalystResponse {
  success: boolean;
  answer: string;
  sql?: string;
  data?: QueryResult;
  suggestions?: string[];
  error?: string;
}

export interface ContentCategory {
  id: string;
  name: string;
  description: string;
}

export interface RevenueMetric {
  category: string;
  quarter: string;
  revenue: number;
  region: string;
  customerSegment: string;
}

export interface VisualContent {
  contentId: string;
  category: string;
  title: string;
  uploadDate: Date;
  licensingRevenue: number;
  downloads: number;
  views: number;
  engagementScore: number;
}
