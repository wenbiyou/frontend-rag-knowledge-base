/**
 * 使用统计页面
 */

"use client";

import { useState, useEffect } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import { StatsCard } from "@/components/StatsCard";
import { SimpleBarChart, SimpleLineChart } from "@/components/SimpleChart";
import {
  MessageSquare,
  Users,
  Clock,
  TrendingUp,
  Calendar,
  BarChart3,
  Loader2,
  RefreshCw,
} from "lucide-react";
import {
  getAnalyticsOverview,
  getAnalyticsDaily,
  getAnalyticsPopular,
  getAnalyticsSources,
  getAnalyticsHourly,
} from "@/lib/api";

interface OverviewStats {
  total_questions: number;
  unique_sessions: number;
  active_days: number;
  avg_response_time_ms: number;
  today_questions: number;
  week_questions: number;
}

interface DailyStat {
  date: string;
  total_questions: number;
  unique_sessions: number;
  avg_response_time_ms: number;
}

interface PopularQuestion {
  question: string;
  count: number;
  unique_askers: number;
}

interface SourceUsage {
  source: string;
  count: number;
}

interface HourlyDistribution {
  hour: number;
  count: number;
}

export default function AnalyticsPage() {
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyStat[]>([]);
  const [popularQuestions, setPopularQuestions] = useState<PopularQuestion[]>(
    [],
  );
  const [sourceUsage, setSourceUsage] = useState<SourceUsage[]>([]);
  const [hourlyDistribution, setHourlyDistribution] = useState<
    HourlyDistribution[]
  >([]);

  const loadData = async () => {
    try {
      const [overviewData, dailyData, popularData, sourcesData, hourlyData] =
        await Promise.all([
          getAnalyticsOverview(),
          getAnalyticsDaily(30),
          getAnalyticsPopular(10),
          getAnalyticsSources(),
          getAnalyticsHourly(),
        ]);

      setOverview(overviewData);
      setDailyStats(dailyData.data);
      setPopularQuestions(popularData.questions);
      setSourceUsage(sourcesData.sources);
      setHourlyDistribution(hourlyData.distribution);
    } catch (error) {
      console.error("加载统计数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadData();
    setRefreshing(false);
  };

  const formatTime = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const getSourceLabel = (source: string) => {
    switch (source) {
      case "official":
        return "官方文档";
      case "github":
        return "GitHub";
      case "all":
        return "全部来源";
      default:
        return source || "全部来源";
    }
  };

  if (loading) {
    return (
      <AdminLayout>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 text-gray-400 animate-spin" />
        </div>
      </AdminLayout>
    );
  }

  return (
    <AdminLayout>
      <div className="max-w-6xl mx-auto">
        {/* 标题栏 */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              使用统计
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              查看系统使用情况和用户行为分析
            </p>
          </div>
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-primary-300 transition-colors"
          >
            <RefreshCw
              className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`}
            />
            <span>刷新</span>
          </button>
        </div>

        {/* 总览卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
          <StatsCard
            label="总提问数"
            value={overview?.total_questions || 0}
            icon={MessageSquare}
            color="text-blue-600"
          />
          <StatsCard
            label="独立会话"
            value={overview?.unique_sessions || 0}
            icon={Users}
            color="text-green-600"
          />
          <StatsCard
            label="活跃天数"
            value={overview?.active_days || 0}
            icon={Calendar}
            color="text-purple-600"
          />
          <StatsCard
            label="平均响应"
            value={formatTime(overview?.avg_response_time_ms || 0)}
            icon={Clock}
            color="text-orange-600"
          />
          <StatsCard
            label="今日提问"
            value={overview?.today_questions || 0}
            icon={TrendingUp}
            color="text-pink-600"
          />
          <StatsCard
            label="本周提问"
            value={overview?.week_questions || 0}
            icon={BarChart3}
            color="text-cyan-600"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* 每日趋势 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              每日提问趋势（近 30 天）
            </h3>
            {dailyStats.length > 0 ? (
              <SimpleLineChart
                data={dailyStats.map((d) => ({
                  label: d.date.slice(5),
                  value: d.total_questions,
                }))}
                height={200}
              />
            ) : (
              <div className="flex items-center justify-center h-48 text-gray-400">
                暂无数据
              </div>
            )}
          </div>

          {/* 小时分布 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              提问时间分布
            </h3>
            <SimpleBarChart
              data={hourlyDistribution.map((d) => ({
                label: `${d.hour}:00`,
                value: d.count,
              }))}
              height={200}
              showLabels={false}
            />
            <div className="flex justify-between text-xs text-gray-400 mt-2">
              <span>0:00</span>
              <span>6:00</span>
              <span>12:00</span>
              <span>18:00</span>
              <span>24:00</span>
            </div>
          </div>

          {/* 热门问题 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              热门问题 TOP 10
            </h3>
            {popularQuestions.length > 0 ? (
              <div className="space-y-3">
                {popularQuestions.map((q, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <span
                      className={`flex-shrink-0 w-6 h-6 rounded-full flex items-center justify-center text-xs font-medium ${
                        index < 3
                          ? "bg-primary-100 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400"
                          : "bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400"
                      }`}
                    >
                      {index + 1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-gray-900 dark:text-white truncate">
                        {q.question}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        提问 {q.count} 次 · {q.unique_askers} 人
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-48 text-gray-400">
                暂无数据
              </div>
            )}
          </div>

          {/* 来源使用 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
              来源使用统计
            </h3>
            {sourceUsage.length > 0 ? (
              <div className="space-y-3">
                {sourceUsage.map((s, index) => {
                  const total = sourceUsage.reduce(
                    (sum, item) => sum + item.count,
                    0,
                  );
                  const percentage = ((s.count / total) * 100).toFixed(1);
                  return (
                    <div key={index} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="text-gray-700 dark:text-gray-300">
                          {getSourceLabel(s.source)}
                        </span>
                        <span className="text-gray-500 dark:text-gray-400">
                          {s.count} 次 ({percentage}%)
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-primary-500 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${percentage}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="flex items-center justify-center h-48 text-gray-400">
                暂无数据
              </div>
            )}
          </div>
        </div>
      </div>
    </AdminLayout>
  );
}
