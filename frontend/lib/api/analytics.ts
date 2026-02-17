import { API_BASE } from './config';
import type { AnalyticsOverview, DailyStat, PopularQuestion, SourceUsage, HourlyDistribution } from './types';

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
