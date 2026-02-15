/**
 * 聊天状态管理 Hook
 * 管理会话、消息列表、发送消息等功能
 * 支持对话历史持久化
 */

import { useState, useCallback, useRef } from 'react';
import {
  ChatMessage,
  Source,
  sendChatMessage,
  sendStreamChatMessage,
  clearSession,
  getSessionMessages,
} from '@/lib/api';

interface UseChatOptions {
  enableStream?: boolean;
}

interface UseChatReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  sessionId: string | null;
  sendMessage: (content: string, sourceFilter?: string) => Promise<void>;
  clearChat: () => void;
  loadSession: (sid: string) => Promise<void>;
  startNewChat: () => void;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { enableStream = true } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // 使用 ref 存储当前正在流式接收的消息内容
  const currentStreamContent = useRef('');
  const currentSources = useRef<Source[]>([]);
  const assistantMessageIndexRef = useRef<number>(0);

  const sendMessage = useCallback(
    async (content: string, sourceFilter?: string) => {
      if (!content.trim() || isLoading) return;

      // 添加用户消息
      const userMessage: ChatMessage = {
        role: 'user',
        content: content.trim(),
      };

      setMessages((prev) => [...prev, userMessage]);
      setIsLoading(true);

      // 添加一个空的助手消息占位，使用函数式更新获取最新索引
      setMessages((prev) => {
        assistantMessageIndexRef.current = prev.length;
        const assistantMessage: ChatMessage = {
          role: 'assistant',
          content: '',
          isStreaming: true,
        };
        return [...prev, assistantMessage];
      });
      currentStreamContent.current = '';
      currentSources.current = [];

      try {
        if (enableStream) {
          // 流式请求
          for await (const chunk of sendStreamChatMessage({
            message: content,
            session_id: sessionId || undefined,
            source_filter: sourceFilter,
          })) {
            if (chunk.type === 'sources') {
              currentSources.current = chunk.data;
            } else if (chunk.type === 'content') {
              currentStreamContent.current += chunk.data;
              // 更新消息内容
              setMessages((prev) => {
                const newMessages = [...prev];
                const idx = assistantMessageIndexRef.current;
                if (newMessages[idx] && newMessages[idx].role === 'assistant') {
                  newMessages[idx] = {
                    ...newMessages[idx],
                    content: currentStreamContent.current,
                    sources: currentSources.current,
                    isStreaming: true,
                  };
                }
                return newMessages;
              });
            } else if (chunk.type === 'error') {
              throw new Error(chunk.data);
            }
          }

          // 流式完成，更新最终状态
          setMessages((prev) => {
            const newMessages = [...prev];
            const idx = assistantMessageIndexRef.current;
            if (newMessages[idx] && newMessages[idx].role === 'assistant') {
              newMessages[idx] = {
                ...newMessages[idx],
                isStreaming: false,
              };
            }
            return newMessages;
          });
        } else {
          // 非流式请求
          const response = await sendChatMessage({
            message: content,
            session_id: sessionId || undefined,
            source_filter: sourceFilter,
          });

          setMessages((prev) => {
            const newMessages = [...prev];
            const idx = assistantMessageIndexRef.current;
            if (newMessages[idx] && newMessages[idx].role === 'assistant') {
              newMessages[idx] = {
                ...newMessages[idx],
                content: response.answer,
                sources: response.sources,
                isStreaming: false,
              };
            }
            return newMessages;
          });

          // 更新会话 ID
          setSessionId(response.session_id);
        }
      } catch (error) {
        console.error('发送消息失败:', error);
        // 显示错误消息
        setMessages((prev) => {
          const newMessages = [...prev];
          const idx = assistantMessageIndexRef.current;
          if (newMessages[idx] && newMessages[idx].role === 'assistant') {
            newMessages[idx] = {
              ...newMessages[idx],
              content: `抱歉，发生了错误：${
                error instanceof Error ? error.message : '未知错误'
              }`,
              isStreaming: false,
            };
          }
          return newMessages;
        });
      } finally {
        setIsLoading(false);
      }
    },
    [messages, sessionId, isLoading, enableStream]
  );

  const clearChat = useCallback(async () => {
    if (sessionId) {
      await clearSession(sessionId);
    }
    setMessages([]);
    setSessionId(null);
  }, [sessionId]);

  // 加载历史会话
  const loadSession = useCallback(async (sid: string) => {
    try {
      const data = await getSessionMessages(sid);
      setSessionId(sid);
      // 转换消息格式
      const loadedMessages: ChatMessage[] = data.messages.map((msg: any) => ({
        role: msg.role,
        content: msg.content,
        sources: msg.sources,
        isStreaming: false,
      }));
      setMessages(loadedMessages);
    } catch (error) {
      console.error('加载会话失败:', error);
    }
  }, []);

  // 开始新对话
  const startNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
  }, []);

  return {
    messages,
    isLoading,
    sessionId,
    sendMessage,
    clearChat,
    loadSession,
    startNewChat,
  };
}
