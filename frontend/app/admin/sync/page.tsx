/**
 * 云端同步设置页面
 */

"use client";

import { useState, useEffect, useRef } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import {
  Cloud,
  Download,
  Upload,
  History,
  Loader2,
  CheckCircle,
  AlertCircle,
  FileJson,
  RefreshCw,
} from "lucide-react";
import { getAuthHeaders } from "@/lib/api";

interface SyncConfig {
  provider: string | null;
  endpoint: string | null;
  auto_sync: boolean;
  last_sync: string | null;
}

interface ExportFile {
  filename: string;
  user_id: number;
  exported_at: string;
  sessions_count: number;
}

interface SyncHistory {
  action: string;
  status: string;
  details: string;
  created_at: string;
}

export default function SyncPage() {
  const [config, setConfig] = useState<SyncConfig | null>(null);
  const [exports, setExports] = useState<ExportFile[]>([]);
  const [history, setHistory] = useState<SyncHistory[]>([]);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<{
    type: "success" | "error";
    message: string;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const API_BASE = "/api";

  const loadData = async () => {
    setLoading(true);
    try {
      const [configRes, exportsRes, historyRes] = await Promise.all([
        fetch(`${API_BASE}/sync/config`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/sync/exports`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/sync/history`, { headers: getAuthHeaders() }),
      ]);

      if (configRes.ok) {
        const data = await configRes.json();
        setConfig(data.config);
      }
      if (exportsRes.ok) {
        const data = await exportsRes.json();
        setExports(data.exports);
      }
      if (historyRes.ok) {
        const data = await historyRes.json();
        setHistory(data.history);
      }
    } catch (error) {
      console.error("加载数据失败:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleExport = async () => {
    setExporting(true);
    setResult(null);
    try {
      const response = await fetch(`${API_BASE}/sync/export`, {
        method: "POST",
        headers: getAuthHeaders(),
      });

      if (!response.ok) {
        throw new Error("导出失败");
      }

      const data = await response.json();
      setResult({
        type: "success",
        message: `导出成功：${data.sessions_count} 个会话`,
      });
      await loadData();
    } catch (error) {
      setResult({
        type: "error",
        message: error instanceof Error ? error.message : "导出失败",
      });
    } finally {
      setExporting(false);
    }
  };

  const handleImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setImporting(true);
    setResult(null);

    try {
      const text = await file.text();
      const data = JSON.parse(text);

      const response = await fetch(`${API_BASE}/sync/import`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({ data }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "导入失败");
      }

      const result = await response.json();
      setResult({
        type: "success",
        message: result.message,
      });
      await loadData();
    } catch (error) {
      setResult({
        type: "error",
        message: error instanceof Error ? error.message : "导入失败",
      });
    } finally {
      setImporting(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleDownload = (filename: string) => {
    window.open(`${API_BASE}/sync/download/${filename}`, "_blank");
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString("zh-CN");
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
      <div className="max-w-4xl mx-auto">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            云端同步
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            导出或导入您的对话数据
          </p>
        </div>

        {/* 操作区域 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            数据操作
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <button
              onClick={handleExport}
              disabled={exporting}
              className="flex items-center justify-center gap-3 p-4 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors disabled:opacity-50"
            >
              {exporting ? (
                <Loader2 className="w-6 h-6 text-primary-600 animate-spin" />
              ) : (
                <Download className="w-6 h-6 text-primary-600" />
              )}
              <div className="text-left">
                <p className="font-medium text-gray-900 dark:text-white">
                  导出数据
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  将对话历史导出为 JSON 文件
                </p>
              </div>
            </button>

            <label className="flex items-center justify-center gap-3 p-4 border-2 border-dashed border-gray-300 dark:border-gray-600 rounded-xl hover:border-primary-400 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors cursor-pointer">
              {importing ? (
                <Loader2 className="w-6 h-6 text-primary-600 animate-spin" />
              ) : (
                <Upload className="w-6 h-6 text-primary-600" />
              )}
              <div className="text-left">
                <p className="font-medium text-gray-900 dark:text-white">
                  导入数据
                </p>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  从 JSON 文件恢复对话历史
                </p>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".json"
                className="hidden"
                onChange={handleImport}
                disabled={importing}
              />
            </label>
          </div>

          {result && (
            <div
              className={`flex items-center gap-2 mt-4 p-3 rounded-lg ${
                result.type === "success"
                  ? "bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400"
                  : "bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400"
              }`}
            >
              {result.type === "success" ? (
                <CheckCircle className="w-5 h-5" />
              ) : (
                <AlertCircle className="w-5 h-5" />
              )}
              <span>{result.message}</span>
            </div>
          )}
        </div>

        {/* 导出文件列表 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            导出文件
          </h2>

          {exports.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <FileJson className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>暂无导出文件</p>
            </div>
          ) : (
            <div className="space-y-2">
              {exports.map((file) => (
                <div
                  key={file.filename}
                  className="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <div className="flex items-center gap-3">
                    <FileJson className="w-5 h-5 text-gray-400" />
                    <div>
                      <p className="text-sm font-medium text-gray-900 dark:text-white">
                        {file.filename}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-gray-400">
                        {file.sessions_count} 个会话 ·{" "}
                        {formatDate(file.exported_at)}
                      </p>
                    </div>
                  </div>
                  <button
                    onClick={() => handleDownload(file.filename)}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-primary-600 hover:bg-primary-50 dark:hover:bg-primary-900/20 rounded-lg transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    <span>下载</span>
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* 同步历史 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            同步历史
          </h2>

          {history.length === 0 ? (
            <div className="text-center py-8 text-gray-500 dark:text-gray-400">
              <History className="w-12 h-12 mx-auto mb-2 opacity-50" />
              <p>暂无同步记录</p>
            </div>
          ) : (
            <div className="space-y-2">
              {history.map((item, index) => (
                <div
                  key={index}
                  className="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg"
                >
                  <div
                    className={`w-2 h-2 rounded-full ${
                      item.status === "success" ? "bg-green-500" : "bg-red-500"
                    }`}
                  />
                  <div className="flex-1">
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {item.action === "export" ? "导出" : "导入"}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-gray-400">
                      {formatDate(item.created_at)}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </AdminLayout>
  );
}
