export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  sources?: Source[];
  isStreaming?: boolean;
}

export interface Source {
  title: string;
  source: string;
  type: string;
  url?: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  source_filter?: string;
  stream?: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  session_id: string;
}

export interface StatsResponse {
  total_documents: number;
  sources: string[];
}

export interface SyncStatus {
  is_running: boolean;
  current_source: string | null;
  progress: number;
  total: number;
  started_at: string | null;
  completed_at: string | null;
  result: any;
  error: string | null;
}

export interface Suggestion {
  text: string;
  type: 'document' | 'common';
  source?: string;
}

export interface Document {
  id: number;
  source: string;
  title: string;
  source_type: string;
  file_type: string | null;
  chunk_count: number;
  total_chars: number;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface DocumentListResponse {
  documents: Document[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface DocumentStatsResponse {
  total_documents: number;
  total_chunks: number;
  total_chars: number;
  by_type: Record<string, number>;
}

export interface DocumentsQueryParams {
  page?: number;
  page_size?: number;
  source_type?: string;
  status?: string;
  search?: string;
}

export interface AnalyticsOverview {
  total_questions: number;
  unique_sessions: number;
  active_days: number;
  avg_response_time_ms: number;
  today_questions: number;
  week_questions: number;
}

export interface DailyStat {
  date: string;
  total_questions: number;
  unique_sessions: number;
  avg_response_time_ms: number;
}

export interface PopularQuestion {
  question: string;
  count: number;
  unique_askers: number;
}

export interface SourceUsage {
  source: string;
  count: number;
}

export interface HourlyDistribution {
  hour: number;
  count: number;
}
