/**
 * API 客户端
 * 封装与后端的所有通信
 */

const API_BASE = '/api';

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
    headers: { 'Content-Type': 'application/json' },
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
    headers: { 'Content-Type': 'application/json' },
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
  await fetch(`${API_BASE}/session/${sessionId}`, { method: 'DELETE' });
}

/**
 * 获取所有历史会话
 */
export async function getSessions(): Promise<{ sessions: any[]; total: number }> {
  const response = await fetch(`${API_BASE}/sessions`);
  if (!response.ok) {
    throw new Error('获取会话列表失败');
  }
  return response.json();
}

/**
 * 获取指定会话的消息历史
 */
export async function getSessionMessages(sessionId: string): Promise<{ session_id: string; messages: any[] }> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
  if (!response.ok) {
    throw new Error('获取会话消息失败');
  }
  return response.json();
}

/**
 * 重命名会话
 */
export async function renameSession(sessionId: string, title: string): Promise<any> {
  const response = await fetch(`${API_BASE}/sessions/${sessionId}/rename`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
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
