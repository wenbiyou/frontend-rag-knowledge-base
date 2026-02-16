/**
 * 管理后台入口页面
 */

"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AdminLayout } from "@/components/AdminLayout";
import { FileText, BarChart3, ArrowRight, Cloud } from "lucide-react";

const quickActions = [
  {
    title: "文档管理",
    description: "查看、删除已导入的文档",
    icon: FileText,
    href: "/admin/documents",
    color: "bg-blue-500",
  },
  {
    title: "使用统计",
    description: "查看系统使用情况和热门问题",
    icon: BarChart3,
    href: "/admin/analytics",
    color: "bg-green-500",
  },
  {
    title: "云端同步",
    description: "导出或导入对话数据",
    icon: Cloud,
    href: "/admin/sync",
    color: "bg-purple-500",
  },
];

export default function AdminPage() {
  const router = useRouter();

  return (
    <AdminLayout>
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            欢迎使用管理后台
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            管理知识库文档、查看使用统计
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quickActions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.href}
                onClick={() => router.push(action.href)}
                className="flex items-start gap-4 p-6 bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 hover:border-primary-300 dark:hover:border-primary-600 hover:shadow-lg transition-all text-left group"
              >
                <div
                  className={`${action.color} p-3 rounded-lg text-white flex-shrink-0`}
                >
                  <Icon className="w-6 h-6" />
                </div>
                <div className="flex-1 min-w-0">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
                    {action.title}
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {action.description}
                  </p>
                </div>
                <ArrowRight className="w-5 h-5 text-gray-400 group-hover:text-primary-500 group-hover:translate-x-1 transition-all flex-shrink-0" />
              </button>
            );
          })}
        </div>

        <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-xl border border-blue-200 dark:border-blue-800">
          <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-2">
            快速提示
          </h3>
          <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-2">
            <li>• 文档删除后将从知识库中移除，无法恢复</li>
            <li>• 使用统计可以帮助了解用户最关心的问题</li>
            <li>• 定期清理不需要的文档可以提升检索效率</li>
          </ul>
        </div>
      </div>
    </AdminLayout>
  );
}
