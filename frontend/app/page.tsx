/**
 * 主页面
 * 整合聊天界面和侧边栏
 */

"use client";

import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { MessageList } from "@/components/MessageList";
import { ChatInput } from "@/components/ChatInput";
import { useChat } from "@/hooks/useChat";
import { Menu, Trash2 } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const {
    messages,
    isLoading,
    sessionId,
    sendMessage,
    clearChat,
    loadSession,
    startNewChat,
  } = useChat({
    enableStream: true,
  });

  // 处理移动端侧边栏关闭
  const handleSidebarClose = () => setSidebarOpen(false);

  // 处理会话选择（移动端自动关闭侧边栏）
  const handleSessionSelect = (sid: string) => {
    loadSession(sid);
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  // 处理新建对话（移动端自动关闭侧边栏）
  const handleNewChat = () => {
    startNewChat();
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 overflow-hidden">
      {/* 侧边栏 - 桌面端始终显示，移动端可折叠 */}
      <aside
        className={`${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        } fixed inset-y-0 left-0 z-30 w-[280px] sm:w-72 transform transition-transform duration-300 ease-out md:relative md:translate-x-0 shadow-2xl md:shadow-none`}
      >
        <Sidebar
          onSourceFilterChange={setSourceFilter}
          onSessionSelect={handleSessionSelect}
          onNewChat={handleNewChat}
          currentSessionId={sessionId}
        />
      </aside>

      {/* 遮罩层 - 仅在移动端侧边栏打开时显示 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-20 md:hidden transition-opacity"
          onClick={handleSidebarClose}
        />
      )}

      {/* 主内容区 */}
      <main className="flex-1 flex flex-col min-w-0 h-full relative">
        {/* 顶部导航栏 */}
        <header className="bg-white border-b border-gray-200 px-3 sm:px-4 py-2.5 sm:py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors md:hidden touch-feedback"
              aria-label="打开菜单"
            >
              <Menu className="w-5 h-5 text-gray-600" />
            </button>

            <div className="flex items-center gap-2 min-w-0">
              <h1 className="text-base sm:text-lg font-semibold text-gray-900 truncate">
                前端知识库助手
              </h1>
              {sourceFilter && (
                <span className="hidden sm:inline-flex items-center text-xs sm:text-sm text-primary-600 bg-primary-50 px-2 py-0.5 sm:py-1 rounded-full whitespace-nowrap">
                  筛选:{" "}
                  {sourceFilter === "official"
                    ? "官方"
                    : sourceFilter === "github"
                      ? "GitHub"
                      : sourceFilter}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-1 sm:gap-2">
            {sourceFilter && (
              <span className="sm:hidden text-xs text-primary-600 bg-primary-50 px-2 py-0.5 rounded-full">
                已筛选
              </span>
            )}
            <ThemeToggle />
            <button
              onClick={clearChat}
              className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 dark:text-gray-400 dark:hover:text-red-400 dark:hover:bg-red-900/30 rounded-lg transition-colors touch-feedback"
              title="清空对话"
            >
              <Trash2 className="w-4 h-4" />
              <span className="hidden sm:inline">清空对话</span>
            </button>
          </div>
        </header>

        {/* 消息列表 */}
        <div className="flex-1 overflow-hidden">
          <MessageList messages={messages} />
        </div>

        {/* 输入框 */}
        <ChatInput
          onSend={(msg) => sendMessage(msg, sourceFilter || undefined)}
          isLoading={isLoading}
        />
      </main>
    </div>
  );
}
