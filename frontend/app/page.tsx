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
import { UserMenu } from "@/components/UserMenu";

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const {
    messages,
    isLoading,
    sessionId,
    sendMessage,
    clearChat,
    loadSession,
    startNewChat,
    hasMessages,
  } = useChat({
    enableStream: true,
  });

  const handleSidebarClose = () => setSidebarOpen(false);

  const handleSessionSelect = (sid: string) => {
    loadSession(sid);
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  const handleNewChat = () => {
    startNewChat();
    setRefreshKey((prev) => prev + 1);
    if (window.innerWidth < 768) {
      setSidebarOpen(false);
    }
  };

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900 overflow-hidden">
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
          refreshKey={refreshKey}
        />
      </aside>

      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/30 backdrop-blur-sm z-20 md:hidden transition-opacity"
          onClick={handleSidebarClose}
        />
      )}

      <main className="flex-1 flex flex-col min-w-0 h-full relative">
        <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-3 sm:px-4 py-2.5 sm:py-3 flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-2 sm:gap-3 min-w-0">
            <button
              onClick={() => setSidebarOpen(true)}
              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors md:hidden touch-feedback"
              aria-label="打开菜单"
            >
              <Menu className="w-5 h-5 text-gray-600 dark:text-gray-400" />
            </button>

            <div className="flex items-center gap-2 min-w-0">
              <h1 className="text-base sm:text-lg font-semibold text-gray-900 dark:text-white truncate">
                前端知识库助手
              </h1>
              {sourceFilter && (
                <span className="hidden sm:inline-flex items-center text-xs sm:text-sm text-primary-600 bg-primary-50 dark:bg-primary-900/30 px-2 py-0.5 sm:py-1 rounded-full whitespace-nowrap">
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
              <span className="sm:hidden text-xs text-primary-600 bg-primary-50 dark:bg-primary-900/30 px-2 py-0.5 rounded-full">
                已筛选
              </span>
            )}
            <ThemeToggle />
            <button
              onClick={clearChat}
              className="flex items-center gap-1.5 px-2 sm:px-3 py-1.5 text-sm text-gray-600 dark:text-gray-400 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 rounded-lg transition-colors touch-feedback"
              title="清空对话"
            >
              <Trash2 className="w-4 h-4" />
              <span className="hidden sm:inline">清空对话</span>
            </button>
            <UserMenu />
          </div>
        </header>

        <div className="flex-1 overflow-hidden">
          <MessageList messages={messages} />
        </div>

        <ChatInput
          onSend={(msg) => sendMessage(msg, sourceFilter || undefined)}
          isLoading={isLoading}
        />
      </main>
    </div>
  );
}
