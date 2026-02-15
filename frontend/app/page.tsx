/**
 * 主页面
 * 整合聊天界面和侧边栏
 */

'use client';

import { useState } from 'react';
import { Sidebar } from '@/components/Sidebar';
import { MessageList } from '@/components/MessageList';
import { ChatInput } from '@/components/ChatInput';
import { useChat } from '@/hooks/useChat';
import { Menu, X, Trash2 } from 'lucide-react';

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [sourceFilter, setSourceFilter] = useState<string | null>(null);
  const { messages, isLoading, sessionId, sendMessage, clearChat, loadSession, startNewChat } = useChat({
    enableStream: true,
  });

  return (
    <div className="flex h-screen bg-gray-50">
      {/* 侧边栏 - 桌面端始终显示，移动端可折叠 */}
      <div
        className={`${
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        } fixed md:relative z-20 h-full transition-transform duration-300 md:translate-x-0`}
      >
        <Sidebar
          onSourceFilterChange={setSourceFilter}
          onSessionSelect={loadSession}
          onNewChat={startNewChat}
          currentSessionId={sessionId}
        />
      </div>

      {/* 遮罩层 - 仅在移动端侧边栏打开时显示 */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-10 md:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* 主内容区 */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* 顶部导航栏 */}
        <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors md:hidden"
            >
              {sidebarOpen ? (
                <X className="w-5 h-5 text-gray-600" />
              ) : (
                <Menu className="w-5 h-5 text-gray-600" />
              )}
            </button>

            <h1 className="text-lg font-semibold text-gray-900">
              前端知识库助手
            </h1>

            {sourceFilter && (
              <span className="text-sm text-primary-600 bg-primary-50 px-2 py-1 rounded-full">
                筛选: {sourceFilter === 'official' ? '官方文档' : sourceFilter === 'github' ? 'GitHub' : sourceFilter}
              </span>
            )}
          </div>

          <button
            onClick={clearChat}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-600 hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            <span className="hidden sm:inline">清空对话</span>
          </button>
        </header>

        {/* 消息列表 */}
        <MessageList messages={messages} />

        {/* 输入框 */}
        <ChatInput
          onSend={(msg) => sendMessage(msg, sourceFilter || undefined)}
          isLoading={isLoading}
        />
      </div>
    </div>
  );
}
