import { API_BASE } from './config';
import type { SyncStatus } from './types';

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

export async function getSyncStatus(): Promise<SyncStatus> {
  const response = await fetch(`${API_BASE}/sync/status`);
  if (!response.ok) {
    throw new Error('获取同步状态失败');
  }
  return response.json();
}
