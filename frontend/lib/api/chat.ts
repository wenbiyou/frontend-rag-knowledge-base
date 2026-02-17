import { API_BASE, getAuthHeaders } from './config';
import type { ChatRequest, ChatResponse, Source } from './types';

export async function sendChatMessage(
  request: ChatRequest
): Promise<ChatResponse> {
  const response = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    const text = await response.text();
    try {
      const error = JSON.parse(text);
      throw new Error(error.detail || '请求失败');
    } catch {
      throw new Error(text || `请求失败 (${response.status})`);
    }
  }

  return response.json();
}

export async function* sendStreamChatMessage(
  request: ChatRequest
): AsyncGenerator<{ type: string; data: any }, void, unknown> {
  const response = await fetch(`${API_BASE}/chat/stream`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ ...request, stream: true }),
  });

  if (!response.ok) {
    const text = await response.text();
    try {
      const error = JSON.parse(text);
      throw new Error(error.detail || '请求失败');
    } catch {
      throw new Error(text || `请求失败 (${response.status})`);
    }
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

export async function clearSession(sessionId: string): Promise<void> {
  await fetch(`${API_BASE}/session/${sessionId}`, {
    method: 'DELETE',
    headers: getAuthHeaders(),
  });
}

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

export async function getSuggestions(query: string, limit: number = 5): Promise<{ suggestions: any[]; query: string }> {
  const response = await fetch(`${API_BASE}/suggestions?query=${encodeURIComponent(query)}&limit=${limit}`);
  if (!response.ok) {
    throw new Error('获取搜索建议失败');
  }
  return response.json();
}
