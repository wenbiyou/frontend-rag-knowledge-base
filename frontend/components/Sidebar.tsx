/**
 * 侧边栏组件
 * 显示知识库统计、文档来源、管理功能
 */

import { useState, useEffect } from "react";
import {
  Database,
  RefreshCw,
  Upload,
  FileText,
  Globe,
  Github,
  ChevronDown,
  ChevronUp,
  Loader2,
  CheckCircle,
  AlertCircle,
  Plus,
  MessageSquare,
  Trash2,
  Settings,
} from "lucide-react";
import {
  getStats,
  getSources,
  syncDocuments,
  uploadDocument,
  getSessions,
  renameSession,
  clearSession,
} from "@/lib/api";

interface SidebarProps {
  onSourceFilterChange?: (filter: string | null) => void;
  onSessionSelect?: (sessionId: string) => void;
  onNewChat?: () => void;
  currentSessionId?: string | null;
}

export function Sidebar({
  onSourceFilterChange,
  onSessionSelect,
  onNewChat,
  currentSessionId,
}: SidebarProps) {
  const [stats, setStats] = useState<{
    total_documents: number;
    sources: string[];
  } | null>(null);
  const [sources, setSources] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);
  const [expandedSections, setExpandedSections] = useState({
    sources: true,
    upload: false,
    history: true,
  });

  // 历史会话状态
  const [sessions, setSessions] = useState<any[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);

  useEffect(() => {
    loadData();
    loadSessions();
  }, []);

  const loadData = async () => {
    try {
      const [statsData, sourcesData] = await Promise.all([
        getStats(),
        getSources(),
      ]);
      setStats(statsData);
      setSources(sourcesData.sources);
    } catch (error) {
      console.error("加载数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  // 加载历史会话
  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const data = await getSessions();
      setSessions(data.sessions);
    } catch (error) {
      console.error("加载会话列表失败:", error);
    } finally {
      setSessionsLoading(false);
    }
  };

  // 删除会话
  const handleDeleteSession = async (
    sessionId: string,
    e: React.MouseEvent,
  ) => {
    e.stopPropagation();
    try {
      await clearSession(sessionId);
      await loadSessions();
    } catch (error) {
      console.error("删除会话失败:", error);
    }
  };

  const handleSync = async (type: "official" | "github" | "all") => {
    setSyncing(true);
    setSyncResult(null);
    try {
      const result = await syncDocuments(type);
      setSyncResult({ success: true, message: result.message });
      await loadData(); // 刷新数据
    } catch (error) {
      setSyncResult({
        success: false,
        message: error instanceof Error ? error.message : "同步失败",
      });
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return (
      <div className="w-full sm:w-72 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-gray-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="w-full sm:w-72 bg-white dark:bg-gray-900 border-r border-gray-200 dark:border-gray-700 flex flex-col h-full">
      {/* 头部 */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center gap-2 mb-1">
          <Database className="w-5 h-5 text-primary-600" />
          <h2 className="font-semibold text-gray-900">知识库</h2>
        </div>
        <p className="text-sm text-gray-500">
          {stats?.total_documents || 0} 个文档片段
        </p>
      </div>

      {/* 新建对话按钮 */}
      {onNewChat && (
        <div className="p-3 border-b border-gray-200">
          <button
            onClick={onNewChat}
            className="flex items-center justify-center gap-2 w-full px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span>新建对话</span>
          </button>
        </div>
      )}

      {/* 滚动内容 */}
      <div className="flex-1 overflow-y-auto p-4 space-y-6">
        {/* 历史会话 */}
        {onSessionSelect && (
          <div>
            <button
              onClick={() =>
                setExpandedSections((prev) => ({
                  ...prev,
                  history: !prev.history,
                }))
              }
              className="flex items-center justify-between w-full text-sm font-medium text-gray-700 mb-2"
            >
              <span>历史会话 ({sessions.length})</span>
              {expandedSections.history ? (
                <ChevronUp className="w-4 h-4" />
              ) : (
                <ChevronDown className="w-4 h-4" />
              )}
            </button>

            {expandedSections.history && (
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {sessionsLoading ? (
                  <div className="flex items-center justify-center py-4">
                    <Loader2 className="w-4 h-4 text-gray-400 animate-spin" />
                  </div>
                ) : sessions.length === 0 ? (
                  <p className="text-xs text-gray-400 text-center py-2">
                    暂无历史会话
                  </p>
                ) : (
                  sessions.map((session) => (
                    <div
                      key={session.session_id}
                      onClick={() => onSessionSelect(session.session_id)}
                      className={`group flex items-center justify-between w-full px-3 py-3 sm:py-2 text-sm rounded-lg cursor-pointer transition-colors active:scale-[0.98] ${
                        currentSessionId === session.session_id
                          ? "bg-primary-100 text-primary-700"
                          : "text-gray-600 hover:bg-gray-100"
                      }`}
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        <MessageSquare className="w-4 h-4 flex-shrink-0" />
                        <span className="truncate">{session.title}</span>
                      </div>
                      <button
                        onClick={(e) =>
                          handleDeleteSession(session.session_id, e)
                        }
                        className="sm:opacity-0 sm:group-hover:opacity-100 hover:text-red-600 p-2 sm:p-1 rounded sm:rounded-none hover:bg-red-50 sm:hover:bg-transparent transition-all"
                        title="删除会话"
                      >
                        <Trash2 className="w-4 h-4 sm:w-3 sm:h-3" />
                      </button>
                    </div>
                  ))
                )}
              </div>
            )}
          </div>
        )}

        {/* 同步按钮 */}
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-gray-700">同步文档</h3>
          <div className="space-y-1.5">
            <SyncButton
              icon={<Globe className="w-4 h-4" />}
              label="同步官方文档"
              onClick={() => handleSync("official")}
              disabled={syncing}
            />
            <SyncButton
              icon={<Github className="w-4 h-4" />}
              label="同步 GitHub"
              onClick={() => handleSync("github")}
              disabled={syncing}
            />
            <SyncButton
              icon={
                <RefreshCw
                  className={`w-4 h-4 ${syncing ? "animate-spin" : ""}`}
                />
              }
              label="全部同步"
              onClick={() => handleSync("all")}
              disabled={syncing}
              primary
            />
          </div>

          {syncResult && (
            <div
              className={`flex items-center gap-1.5 text-sm ${
                syncResult.success ? "text-green-600" : "text-red-600"
              }`}
            >
              {syncResult.success ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <AlertCircle className="w-4 h-4" />
              )}
              <span className="truncate">{syncResult.message}</span>
            </div>
          )}
        </div>

        {/* 文档来源 */}
        <div>
          <button
            onClick={() =>
              setExpandedSections((prev) => ({
                ...prev,
                sources: !prev.sources,
              }))
            }
            className="flex items-center justify-between w-full text-sm font-medium text-gray-700 mb-2"
          >
            <span>文档来源 ({sources.length})</span>
            {expandedSections.sources ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          {expandedSections.sources && (
            <div className="space-y-1">
              <SourceFilterButton
                label="全部来源"
                count={stats?.total_documents || 0}
                icon={<Database className="w-4 h-4" />}
                onClick={() => onSourceFilterChange?.(null)}
              />
              {sources.map((source, i) => (
                <SourceFilterButton
                  key={i}
                  label={source.title || source.source}
                  count={source.count}
                  icon={getSourceIcon(source.type)}
                  onClick={() => onSourceFilterChange?.(source.type)}
                />
              ))}
            </div>
          )}
        </div>

        {/* 上传文档 */}
        <div>
          <button
            onClick={() =>
              setExpandedSections((prev) => ({ ...prev, upload: !prev.upload }))
            }
            className="flex items-center justify-between w-full text-sm font-medium text-gray-700 mb-2"
          >
            <span>上传文档</span>
            {expandedSections.upload ? (
              <ChevronUp className="w-4 h-4" />
            ) : (
              <ChevronDown className="w-4 h-4" />
            )}
          </button>

          {expandedSections.upload && <UploadForm onSuccess={loadData} />}
        </div>

        {/* 管理入口 */}
        <div className="pt-4 border-t border-gray-200 dark:border-gray-700 mt-4">
          <a
            href="/admin"
            className="flex items-center gap-2 w-full px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-primary-600 dark:hover:text-primary-400 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
          >
            <Settings className="w-4 h-4" />
            <span>管理后台</span>
          </a>
        </div>
      </div>
    </div>
  );
}

function SyncButton({
  icon,
  label,
  onClick,
  disabled,
  primary,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
  primary?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`flex items-center gap-2 w-full px-3 py-3 sm:py-2 rounded-lg text-sm transition-all active:scale-[0.98] ${
        primary
          ? "bg-primary-600 text-white hover:bg-primary-700 disabled:bg-primary-300"
          : "bg-gray-100 text-gray-700 hover:bg-gray-200 disabled:bg-gray-50 disabled:text-gray-400"
      }`}
    >
      {icon}
      <span>{label}</span>
    </button>
  );
}

function SourceFilterButton({
  label,
  count,
  icon,
  onClick,
}: {
  label: string;
  count: number;
  icon: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center justify-between w-full px-3 py-3 sm:py-2 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-all active:scale-[0.98] active:bg-gray-200"
    >
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <span className="text-gray-400 flex-shrink-0">{icon}</span>
        <span className="truncate">{label}</span>
      </div>
      <span className="text-gray-400 text-xs flex-shrink-0 ml-2">{count}</span>
    </button>
  );
}

function getSourceIcon(type: string) {
  switch (type) {
    case "official":
      return <Globe className="w-4 h-4" />;
    case "github":
      return <Github className="w-4 h-4" />;
    default:
      return <FileText className="w-4 h-4" />;
  }
}

function UploadForm({ onSuccess }: { onSuccess: () => void }) {
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState<{
    current: number;
    total: number;
    status: string;
  } | null>(null);
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
    details?: {
      total_files?: number;
      success_count?: number;
      error_count?: number;
      total_chunks?: number;
    };
  } | null>(null);

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setResult(null);
    setProgress({ current: 0, total: 1, status: "上传中..." });

    try {
      const response = await uploadDocument(file);

      if (response.total_files) {
        setResult({
          success: true,
          message: response.message,
          details: {
            total_files: response.total_files,
            success_count: response.success_count,
            error_count: response.error_count,
            total_chunks: response.total_chunks,
          },
        });
      } else {
        setResult({ success: true, message: response.message || "上传成功" });
      }
      onSuccess();
    } catch (error) {
      setResult({
        success: false,
        message: error instanceof Error ? error.message : "上传失败",
      });
    } finally {
      setUploading(false);
      setProgress(null);
    }
  };

  return (
    <div className="space-y-2">
      <label className="flex flex-col items-center justify-center w-full h-24 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-lg cursor-pointer hover:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors">
        <div className="flex flex-col items-center justify-center pt-5 pb-6">
          <Upload
            className={`w-6 h-6 text-gray-400 dark:text-gray-500 mb-2 ${uploading ? "animate-bounce" : ""}`}
          />
          <p className="text-xs text-gray-500 dark:text-gray-400">
            点击或拖拽上传
          </p>
          <p className="text-xs text-gray-400 dark:text-gray-500">
            支持 Markdown、TXT、PDF、ZIP
          </p>
        </div>
        <input
          type="file"
          className="hidden"
          accept=".md,.markdown,.txt,.pdf,.zip"
          onChange={handleFileChange}
          disabled={uploading}
        />
      </label>

      {progress && (
        <div className="text-xs text-center text-primary-600 dark:text-primary-400">
          {progress.status}
        </div>
      )}

      {result && (
        <div
          className={`text-xs text-center ${
            result.success
              ? "text-green-600 dark:text-green-400"
              : "text-red-600 dark:text-red-400"
          }`}
        >
          <p>{result.message}</p>
          {result.details && (
            <p className="mt-1 text-gray-500 dark:text-gray-400">
              成功 {result.details.success_count} 个 · 片段{" "}
              {result.details.total_chunks} 个
            </p>
          )}
        </div>
      )}
    </div>
  );
}
