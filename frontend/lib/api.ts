/**
 * API 客户端
 * 封装与后端的所有通信
 */

const API_BASE = '/api';

export function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

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

/**
 * 发送对话请求（非流式）
 */
export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '请求失败');
  }

  return response.json();
}

/**
 * 发送流式对话请求
 * 返回一个异步生成器，可以实时获取生成的内容
 */
export async function* sendStreamChatMessage(
  request: ChatRequest
): AsyncGenerator<{ type: string; data: any }, void, unknown> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ ...request, stream: true }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '请求失败');
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error('无法读取响应');
  }

  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });

    // 处理 SSE 格式的数据
    const lines = buffer.split('\n\n');
    buffer = lines.pop() || '';

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6));
          yield data;
        } catch (e) {
          console.error('解析 SSE 数据失败:', line);
        }
      }
    }
  }
}

/**
 * 获取知识库统计信息
 */
export async function getStats(): Promise<StatsResponse> {
  const response = await fetch(`${API_BASE}/stats`);
  if (!response.ok) {
    throw new Error('获取统计信息失败');
  }
  return response.json();
}

/**
 * 获取所有文档来源
 */
export async function getSources(): Promise<{ sources: any[]; total: number }> {
  const response = await fetch(`${API_BASE}/sources`);
  if (!response.ok) {
    throw new Error('获取来源失败');
  }
  return response.json();
}

/**
 * 上传文档
 */
export async function uploadDocument(
  file: File,
  title?: string,
  description?: string
): Promise<any> {
  const formData = new FormData();
  formData.append('file', file);
  if (title) formData.append('title', title);
  if (description) formData.append('description', description);

  const response = await fetch(`${API_BASE}/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '上传失败');
  }

  return response.json();
}

/**
 * 触发文档同步
 */
export async function syncDocuments(source: 'official' | 'github' | 'all' = 'all'): Promise<any> {
  const response = await fetch(`${API_BASE}/sync`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ source }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '同步失败');
  }

  return response.json();
}

/**
 * 清空会话
 */
export async function clearSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/session/${sessionId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
}

/**
 * 获取所有历史会话
 */
export async function getSessions(): Promise<{ sessions: any[]; total: number }> {
  const response = await fetch(`${API_BASE}/sessions`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('获取会话列表失败');
  }
  return response.json();
}

export async function getSessionMessages(sessionId: string): Promise<{ session_id: string; messages: any[] }> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`, {
    headers: getAuthHeaders(),
  });
  if (!response.ok) {
    throw new Error('获取会话消息失败');
  }
  return response.json();
}

export async function renameSession(sessionId: string, title: string): Promise<any> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/rename`, {
    method: 'PUT',
    headers: getAuthHeaders(),
    body: JSON.stringify({ title }),
  });
  if (!response.ok) {
    throw new Error('重命名会话失败');
  }
  return response.json();
}

export interface Suggestion {
  text: string;
  type: 'document' | 'common';
  source?: string;
}

/**
 * 获取搜索建议
 */
export async function getSuggestions(query: string, limit: number = 5): Promise<{ suggestions: Suggestion[]; query: string }> {
  const response = await fetch(`${API_BASE}/suggestions?query=${encodeURIComponent(query)}&limit=${limit}`);
  if (!response.ok) {
    throw new Error('获取搜索建议失败');
  }
  return response.json();
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

export async function getDocuments(params: DocumentsQueryParams = {}): Promise<DocumentListResponse> {
  const searchParams = new URLSearchParams();
  if (params.page) searchParams.set('page', params.page.toString());
  if (params.page_size) searchParams.set('page_size', params.page_size.toString());
  if (params.source_type) searchParams.set('source_type', params.source_type);
  if (params.status) searchParams.set('status', params.status);
  if (params.search) searchParams.set('search', params.search);

  const response = await fetch(`${API_BASE}/documents?${searchParams.toString()}`);
  if (!response.ok) {
    throw new Error('获取文档列表失败');
  }
  return response.json();
}

export async function getDocumentStats(): Promise<DocumentStatsResponse> {
  const response = await fetch(`${API_BASE}/documents/stats`);
  if (!response.ok) {
    throw new Error('获取文档统计失败');
  }
  return response.json();
}

export async function deleteDocument(source: string): Promise<{ success: boolean; message: string }> {
  const response = await fetch(`${API_BASE}/documents/${encodeURIComponent(source)}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '删除文档失败');
  }
  return response.json();
}

export async function syncDocumentsFromVectorStore(): Promise<{ success: boolean; message: string; count: number }> {
  const response = await fetch(`${API_BASE}/documents/sync`, {
    method: 'POST',
  });
  if (!response.ok) {
    throw new Error('同步文档失败');
  }
  return response.json();
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

export async function getAnalyticsOverview(): Promise<AnalyticsOverview> {
  const response = await fetch(`${API_BASE}/analytics/overview`);
  if (!response.ok) {
    throw new Error('获取统计总览失败');
  }
  return response.json();
}

export async function getAnalyticsDaily(days: number = 30): Promise<{ days: number; data: DailyStat[] }> {
  const response = await fetch(`${API_BASE}/analytics/daily?days=${days}`);
  if (!response.ok) {
    throw new Error('获取每日统计失败');
  }
  return response.json();
}

export async function getAnalyticsPopular(limit: number = 20): Promise<{ questions: PopularQuestion[] }> {
  const response = await fetch(`${API_BASE}/analytics/popular?limit=${limit}`);
  if (!response.ok) {
    throw new Error('获取热门问题失败');
  }
  return response.json();
}

export async function getAnalyticsSources(): Promise<{ sources: SourceUsage[] }> {
  const response = await fetch(`${API_BASE}/analytics/sources`);
  if (!response.ok) {
    throw new Error('获取来源统计失败');
  }
  return response.json();
}

export async function getAnalyticsHourly(): Promise<{ distribution: HourlyDistribution[] }> {
  const response = await fetch(`${API_BASE}/analytics/hourly`);
  if (!response.ok) {
    throw new Error('获取小时分布失败');
  }
  return response.json();
}
