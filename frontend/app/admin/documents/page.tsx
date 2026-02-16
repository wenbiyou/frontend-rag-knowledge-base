/**
 * 文档管理页面
 */

"use client";

import { useState, useEffect, useCallback } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import {
  FileText,
  Search,
  Trash2,
  RefreshCw,
  Globe,
  Github,
  Loader2,
  AlertCircle,
  ChevronLeft,
  ChevronRight,
  Database,
} from "lucide-react";
import {
  getDocuments,
  getDocumentStats,
  deleteDocument,
  syncDocumentsFromVectorStore,
} from "@/lib/api";

interface Document {
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

interface DocumentStats {
  total_documents: number;
  total_chunks: number;
  total_chars: number;
  by_type: Record<string, number>;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [stats, setStats] = useState<DocumentStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [search, setSearch] = useState("");
  const [sourceType, setSourceType] = useState<string>("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);

  const loadDocuments = useCallback(async () => {
    setLoading(true);
    try {
      const [docsData, statsData] = await Promise.all([
        getDocuments({
          page,
          page_size: 10,
          search: search || undefined,
          source_type: sourceType || undefined,
        }),
        getDocumentStats(),
      ]);
      setDocuments(docsData.documents);
      setTotal(docsData.total);
      setTotalPages(docsData.total_pages);
      setStats(statsData);
    } catch (error) {
      console.error("加载文档失败:", error);
    } finally {
      setLoading(false);
    }
  }, [page, search, sourceType]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      await syncDocumentsFromVectorStore();
      await loadDocuments();
    } catch (error) {
      console.error("同步失败:", error);
    } finally {
      setSyncing(false);
    }
  };

  const handleDelete = async (source: string) => {
    setDeleting(source);
    try {
      await deleteDocument(source);
      await loadDocuments();
      setDeleteConfirm(null);
    } catch (error) {
      console.error("删除失败:", error);
    } finally {
      setDeleting(null);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadDocuments();
  };

  const getSourceIcon = (type: string) => {
    switch (type) {
      case "official":
        return <Globe className="w-4 h-4" />;
      case "github":
        return <Github className="w-4 h-4" />;
      default:
        return <FileText className="w-4 h-4" />;
    }
  };

  const getSourceLabel = (type: string) => {
    switch (type) {
      case "official":
        return "官方文档";
      case "github":
        return "GitHub";
      default:
        return "本地文档";
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatBytes = (chars: number) => {
    if (chars < 1024) return `${chars} 字符`;
    if (chars < 1024 * 1024) return `${(chars / 1024).toFixed(1)} KB`;
    return `${(chars / 1024 / 1024).toFixed(1)} MB`;
  };

  return (
    <AdminLayout>
      <div className="max-w-6xl mx-auto">
        {/* 统计卡片 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <StatCard
            label="文档总数"
            value={stats?.total_documents || 0}
            icon={<FileText className="w-5 h-5" />}
            color="text-blue-600"
          />
          <StatCard
            label="文档片段"
            value={stats?.total_chunks || 0}
            icon={<FileText className="w-5 h-5" />}
            color="text-green-600"
          />
          <StatCard
            label="总字符数"
            value={formatBytes(stats?.total_chars || 0)}
            icon={<FileText className="w-5 h-5" />}
            color="text-purple-600"
          />
          <StatCard
            label="来源类型"
            value={Object.keys(stats?.by_type || {}).length}
            icon={<Globe className="w-5 h-5" />}
            color="text-orange-600"
          />
        </div>

        {/* 工具栏 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4 mb-6">
          <div className="flex flex-col sm:flex-row gap-4">
            {/* 搜索框 */}
            <form onSubmit={handleSearch} className="flex-1">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索文档标题或来源..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                />
              </div>
            </form>

            {/* 类型筛选 */}
            <select
              value={sourceType}
              onChange={(e) => {
                setSourceType(e.target.value);
                setPage(1);
              }}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
            >
              <option value="">全部类型</option>
              <option value="official">官方文档</option>
              <option value="github">GitHub</option>
              <option value="document">本地文档</option>
            </select>

            {/* 同步按钮 */}
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-primary-300 transition-colors"
            >
              {syncing ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Database className="w-4 h-4" />
              )}
              <span>同步</span>
            </button>
          </div>
        </div>

        {/* 文档列表 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
            </div>
          ) : documents.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-gray-500">
              <FileText className="w-12 h-12 mb-4 text-gray-300" />
              <p>暂无文档</p>
              <p className="text-sm text-gray-400 mt-1">
                点击「同步」按钮从向量数据库导入文档信息
              </p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 dark:bg-gray-700/50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        文档
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden sm:table-cell">
                        类型
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                        片段数
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden md:table-cell">
                        大小
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider hidden lg:table-cell">
                        更新时间
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                    {documents.map((doc) => (
                      <tr
                        key={doc.id}
                        className="hover:bg-gray-50 dark:hover:bg-gray-700/50"
                      >
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-2 min-w-0">
                            <span className="text-gray-400 flex-shrink-0">
                              {getSourceIcon(doc.source_type)}
                            </span>
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
                                {doc.title}
                              </p>
                              <p className="text-xs text-gray-500 dark:text-gray-400 truncate">
                                {doc.source}
                              </p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 hidden sm:table-cell">
                          <span
                            className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                              doc.source_type === "official"
                                ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                                : doc.source_type === "github"
                                  ? "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                                  : "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                            }`}
                          >
                            {getSourceLabel(doc.source_type)}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 hidden md:table-cell">
                          {doc.chunk_count}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 hidden md:table-cell">
                          {formatBytes(doc.total_chars)}
                        </td>
                        <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 hidden lg:table-cell">
                          {formatDate(doc.updated_at)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {deleteConfirm === doc.source ? (
                            <div className="flex items-center justify-end gap-2">
                              <button
                                onClick={() => handleDelete(doc.source)}
                                disabled={deleting === doc.source}
                                className="flex items-center gap-1 px-2 py-1 text-xs bg-red-600 text-white rounded hover:bg-red-700 disabled:bg-red-300"
                              >
                                {deleting === doc.source ? (
                                  <Loader2 className="w-3 h-3 animate-spin" />
                                ) : (
                                  <AlertCircle className="w-3 h-3" />
                                )}
                                确认
                              </button>
                              <button
                                onClick={() => setDeleteConfirm(null)}
                                className="px-2 py-1 text-xs text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
                              >
                                取消
                              </button>
                            </div>
                          ) : (
                            <button
                              onClick={() => setDeleteConfirm(doc.source)}
                              className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors"
                              title="删除文档"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* 分页 */}
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-gray-700">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    共 {total} 条记录
                  </p>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronLeft className="w-5 h-5" />
                    </button>
                    <span className="text-sm text-gray-600 dark:text-gray-300">
                      {page} / {totalPages}
                    </span>
                    <button
                      onClick={() =>
                        setPage((p) => Math.min(totalPages, p + 1))
                      }
                      disabled={page === totalPages}
                      className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      <ChevronRight className="w-5 h-5" />
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}

function StatCard({
  label,
  value,
  icon,
  color,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  color: string;
}) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center gap-3">
        <div className={`${color}`}>{icon}</div>
        <div>
          <p className="text-xs text-gray-500 dark:text-gray-400">{label}</p>
          <p className="text-lg font-semibold text-gray-900 dark:text-white">
            {value}
          </p>
        </div>
      </div>
    </div>
  );
}
