/**
 * 聊天状态管理 Hook
 * 管理会话、消息列表、发送消息等功能
 * 支持对话历史持久化
 * 
 * 优化：使用 flushSync + requestAnimationFrame 实现实时流式显示
 */

import { useState, useCallback, useRef } from 'react';
import { flushSync } from 'react-dom';
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
  status: string;
  isCached: boolean;
  sendMessage: (content: string, sourceFilter?: string) => Promise<void>;
  clearChat: () => void;
  loadSession: (sid: string) => Promise<void>;
  startNewChat: () => void;
  hasMessages: boolean;
}

export function useChat(options: UseChatOptions = {}): UseChatReturn {
  const { enableStream = true } = options;

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [status, setStatus] = useState('');
  const [isCached, setIsCached] = useState(false);

  const currentStreamContent = useRef('');
  const currentSources = useRef<Source[]>([]);
  const assistantMessageIndexRef = useRef<number>(0);
  const lastRenderTimeRef = useRef<number>(0);
  const pendingContentRef = useRef<string>('');
  const rafIdRef = useRef<number | null>(null);

  const updateStreamingMessage = useCallback(() => {
    if (pendingContentRef.current === '') return;
    
    const contentToUpdate = pendingContentRef.current;
    pendingContentRef.current = '';
    
    flushSync(() => {
      setMessages((prev) => {
        const newMessages = [...prev];
        const idx = assistantMessageIndexRef.current;
        if (newMessages[idx] && newMessages[idx].role === 'assistant') {
          newMessages[idx] = {
            ...newMessages[idx],
            content: contentToUpdate,
            sources: currentSources.current,
            isStreaming: true,
          };
        }
        return newMessages;
      });
    });
    
    lastRenderTimeRef.current = performance.now();
  }, []);

  const scheduleRender = useCallback(() => {
    if (rafIdRef.current !== null) {
      return;
    }
    
    const now = performance.now();
    const timeSinceLastRender = now - lastRenderTimeRef.current;
    const minFrameTime = 16;
    
    if (timeSinceLastRender >= minFrameTime) {
      updateStreamingMessage();
    } else {
      rafIdRef.current = requestAnimationFrame(() => {
        rafIdRef.current = null;
        updateStreamingMessage();
      });
    }
  }, [updateStreamingMessage]);

  const sendMessage = useCallback(
    async (content: string, sourceFilter?: string) => {
      if (!content.trim() || isLoading) return;

      const userMessage: ChatMessage = {
        role: 'user',
        content: content.trim(),
      };

      flushSync(() => {
        setMessages((prev) => [...prev, userMessage]);
      });
      setIsLoading(true);

      flushSync(() => {
        setMessages((prev) => {
          assistantMessageIndexRef.current = prev.length;
          const assistantMessage: ChatMessage = {
            role: 'assistant',
            content: '',
            isStreaming: true,
          };
          return [...prev, assistantMessage];
        });
      });
      
      currentStreamContent.current = '';
      pendingContentRef.current = '';
      currentSources.current = [];
      lastRenderTimeRef.current = 0;
      setStatus('正在连接...');
      setIsCached(false);

      try {
        if (enableStream) {
          for await (const chunk of sendStreamChatMessage({
            message: content,
            session_id: sessionId || undefined,
            source_filter: sourceFilter,
          })) {
            if (chunk.type === 'session_id') {
              setSessionId(chunk.data);
            } else if (chunk.type === 'sources') {
              currentSources.current = chunk.data;
            } else if (chunk.type === 'status') {
              setStatus(chunk.data);
            } else if (chunk.type === 'cached') {
              setIsCached(true);
              setStatus('来自缓存');
            } else if (chunk.type === 'content') {
              currentStreamContent.current += chunk.data;
              pendingContentRef.current = currentStreamContent.current;
              scheduleRender();
            } else if (chunk.type === 'error') {
              throw new Error(chunk.data);
            }
          }

          if (rafIdRef.current !== null) {
            cancelAnimationFrame(rafIdRef.current);
            rafIdRef.current = null;
          }
          updateStreamingMessage();

          flushSync(() => {
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
          });
        } else {
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

          setSessionId(response.session_id);
        }
      } catch (error) {
        console.error('发送消息失败:', error);
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
    [messages, sessionId, isLoading, enableStream, scheduleRender, updateStreamingMessage]
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

  const startNewChat = useCallback(() => {
    setMessages([]);
    setSessionId(null);
    setStatus('');
    setIsCached(false);
  }, []);

  return {
    messages,
    isLoading,
    sessionId,
    status,
    isCached,
    sendMessage,
    clearChat,
    loadSession,
    startNewChat,
    hasMessages: messages.length > 0,
  };
}
