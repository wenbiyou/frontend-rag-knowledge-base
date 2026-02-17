import { API_BASE } from './config';
import type { Document, DocumentListResponse, DocumentStatsResponse, DocumentsQueryParams } from './types';

export async function getStats(): Promise<{ total_documents: number; sources: string[] }> {
  const response = await fetch(`${API_BASE}/stats`);
  if (!response.ok) {
    throw new Error('获取统计信息失败');
  }
  return response.json();
}

export async function getSources(): Promise<{ sources: any[]; total: number }> {
  const response = await fetch(`${API_BASE}/sources`);
  if (!response.ok) {
    throw new Error('获取来源失败');
  }
  return response.json();
}

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
