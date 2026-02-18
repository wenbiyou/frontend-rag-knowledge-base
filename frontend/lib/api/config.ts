/**
 * API 配置
 * 
 * 重要：开发环境直接连接后端 API，绕过 Next.js rewrites 代理
 * Next.js rewrites 会缓冲整个 SSE 响应，导致流式输出失效
 */

const isDev = process.env.NODE_ENV === 'development';
const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

const API_BASE = isDev ? `${BACKEND_URL}/api` : '/api';

export function getAuthHeaders(): Record<string, string> {
  const token = typeof window !== 'undefined' ? localStorage.getItem('auth_token') : null;
  const headers: Record<string, string> = { 'Content-Type': 'application/json' };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export { API_BASE, BACKEND_URL };
