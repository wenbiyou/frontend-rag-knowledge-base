/**
 * API Key 管理页面
 */

"use client";

import { useState, useEffect } from "react";
import { AdminLayout } from "@/components/AdminLayout";
import {
  Key,
  Plus,
  Trash2,
  Copy,
  Loader2,
  CheckCircle,
  Code,
} from "lucide-react";
import { getAuthHeaders } from "@/lib/api";

interface APIKey {
  id: number;
  key_prefix: string;
  name: string;
  permissions: string;
  is_active: boolean;
  created_at: string;
  last_used: string | null;
  usage_count: number;
}

interface NewKeyResult {
  id: number;
  name: string;
  key: string;
  key_prefix: string;
  permissions: string;
  created_at: string;
  warning: string;
}

export default function APIKeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [stats, setStats] = useState({ total_keys: 0, active_keys: 0, total_usage: 0 });
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newKeyName, setNewKeyName] = useState("");
  const [newKeyResult, setNewKeyResult] = useState<NewKeyResult | null>(null);
  const [copied, setCopied] = useState(false);

  const API_BASE = "/api";

  const loadData = async () => {
    setLoading(true);
    try {
      const [keysRes, statsRes] = await Promise.all([
        fetch(`${API_BASE}/keys`, { headers: getAuthHeaders() }),
        fetch(`${API_BASE}/keys/stats`, { headers: getAuthHeaders() }),
      ]);

      if (keysRes.ok) {
        const data = await keysRes.json();
        setKeys(data.keys);
      }
      if (statsRes.ok) {
        setStats(await statsRes.json());
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

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) return;

    setCreating(true);
    try {
      const response = await fetch(`${API_BASE}/keys`, {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify({
          name: newKeyName,
          permissions: "read",
        }),
      });

      if (!response.ok) {
        throw new Error("创建失败");
      }

      const data = await response.json();
      setNewKeyResult(data);
      setNewKeyName("");
      await loadData();
    } catch (error) {
      console.error("创建 API Key 失败:", error);
    } finally {
      setCreating(false);
    }
  };

  const handleDeleteKey = async (keyId: number) => {
    if (!confirm("确定要删除此 API Key 吗？")) return;

    try {
      const response = await fetch(`${API_BASE}/keys/${keyId}`, {
        method: "DELETE",
        headers: getAuthHeaders(),
      });

      if (response.ok) {
        await loadData();
      }
    } catch (error) {
      console.error("删除失败:", error);
    }
  };

  const handleCopyKey = (key: string) => {
    navigator.clipboard.writeText(key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const formatDate = (dateStr: string | null) => {
    if (!dateStr) return "从未使用";
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
            API Key 管理
          </h1>
          <p className="text-gray-600 dark:text-gray-400 mt-1">
            创建和管理 API Key，用于第三方系统集成
          </p>
        </div>

        {/* 统计卡片 */}
        <div className="grid grid-cols-3 gap-4 mb-6">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">总 Key 数</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.total_keys}
            </p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">活跃 Key</p>
            <p className="text-2xl font-bold text-green-600">{stats.active_keys}</p>
          </div>
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <p className="text-sm text-gray-500 dark:text-gray-400">总调用次数</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {stats.total_usage}
            </p>
          </div>
        </div>

        {/* 创建新 Key */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
            创建新 API Key
          </h2>

          {newKeyResult ? (
            <div className="space-y-4">
              <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
                <CheckCircle className="w-5 h-5 text-green-600" />
                <span className="text-green-700 dark:text-green-400">
                  API Key 创建成功！
                </span>
              </div>

              <div className="p-4 bg-gray-100 dark:bg-gray-700 rounded-lg">
                <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
                  API Key（请立即保存，仅显示一次）：
                </p>
                <div className="flex items-center gap-2">
                  <code className="flex-1 text-sm font-mono text-gray-900 dark:text-white break-all">
                    {newKeyResult.key}
                  </code>
                  <button
                    onClick={() => handleCopyKey(newKeyResult.key || "")}
                    className="p-2 hover:bg-gray-200 dark:hover:bg-gray-600 rounded"
                  >
                    {copied ? (
                      <CheckCircle className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4 text-gray-400" />
                    )}
                  </button>
                </div>
              </div>

              <button
                onClick={() => setNewKeyResult(null)}
                className="px-4 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white"
              >
                创建另一个 Key
              </button>
            </div>
          ) : (
            <div className="flex gap-3">
              <input
                type="text"
                value={newKeyName}
                onChange={(e) => setNewKeyName(e.target.value)}
                placeholder="输入 Key 名称（如：生产环境、测试环境）"
                className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary-500"
              />
              <button
                onClick={handleCreateKey}
                disabled={creating || !newKeyName.trim()}
                className="flex items-center gap-2 px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-primary-300 transition-colors"
              >
                {creating ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Plus className="w-4 h-4" />
                )}
                <span>创建</span>
              </button>
            </div>
          )}
        </div>

        {/* API 文档 */}
        <div className="bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-6 mb-6">
          <h2 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3 flex items-center gap-2">
            <Code className="w-5 h-5" />
            API 使用说明
          </h2>
          <div className="text-sm text-blue-700 dark:text-blue-300 space-y-2">
            <p>
              <strong>认证方式：</strong>在请求头中添加{" "}
              <code className="px-1 py-0.5 bg-blue-100 dark:bg-blue-800 rounded">
                X-API-Key: your_api_key
              </code>
            </p>
            <p>
              <strong>对话接口：</strong>
              <code className="px-1 py-0.5 bg-blue-100 dark:bg-blue-800 rounded">
                POST /api/v1/chat
              </code>
            </p>
            <p>
              <strong>文档接口：</strong>
              <code className="px-1 py-0.5 bg-blue-100 dark:bg-blue-800 rounded">
                GET /api/v1/documents
              </code>
            </p>
          </div>
        </div>

        {/* Key 列表 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-50 dark:bg-gray-700/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  名称
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  Key 前缀
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase hidden sm:table-cell">
                  权限
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase hidden md:table-cell">
                  使用次数
                </th>
                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase hidden lg:table-cell">
                  最后使用
                </th>
                <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">
                  操作
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {keys.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-gray-500 dark:text-gray-400">
                    <Key className="w-8 h-8 mx-auto mb-2 opacity-50" />
                    <p>暂无 API Key</p>
                  </td>
                </tr>
              ) : (
                keys.map((apiKey) => (
                  <tr
                    key={apiKey.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-700/50"
                  >
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Key className="w-4 h-4 text-gray-400" />
                        <span className="font-medium text-gray-900 dark:text-white">
                          {apiKey.name}
                        </span>
                        {!apiKey.is_active && (
                          <span className="text-xs text-red-500">（已禁用）</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <code className="text-sm text-gray-600 dark:text-gray-300">
                        {apiKey.key_prefix}...
                      </code>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span
                        className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                          apiKey.permissions === "read"
                            ? "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400"
                            : "bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400"
                        }`}
                      >
                        {apiKey.permissions === "read" ? "只读" : "读写"}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 hidden md:table-cell">
                      {apiKey.usage_count}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 hidden lg:table-cell">
                      {formatDate(apiKey.last_used)}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() => handleDeleteKey(apiKey.id)}
                        className="p-1.5 text-gray-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/30 rounded transition-colors"
                        title="删除"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </AdminLayout>
  );
}
