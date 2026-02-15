/**
 * 聊天输入框组件
 * 支持搜索建议、自动调整高度
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Send, Loader2, Search, FileText, HelpCircle } from 'lucide-react';
import { getSuggestions, Suggestion } from '@/lib/api';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, isLoading, placeholder }: ChatInputProps) {
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState<Suggestion[]>([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const suggestionsRef = useRef<HTMLDivElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);

  // 自动调整高度
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  // 监听自定义事件（用于快捷输入示例）
  useEffect(() => {
    const handleSetInput = (e: CustomEvent) => {
      setInput(e.detail);
      textareaRef.current?.focus();
    };

    window.addEventListener('setInput', handleSetInput as EventListener);
    return () => {
      window.removeEventListener('setInput', handleSetInput as EventListener);
    };
  }, []);

  // 点击外部关闭建议
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        suggestionsRef.current &&
        !suggestionsRef.current.contains(e.target as Node) &&
        textareaRef.current &&
        !textareaRef.current.contains(e.target as Node)
      ) {
        setShowSuggestions(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // 获取搜索建议（防抖）
  const fetchSuggestions = useCallback(async (query: string) => {
    if (!query.trim() || query.trim().length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    try {
      const data = await getSuggestions(query, 5);
      if (data.suggestions.length > 0) {
        setSuggestions(data.suggestions);
        setShowSuggestions(true);
        setSelectedIndex(-1);
      } else {
        setShowSuggestions(false);
      }
    } catch (error) {
      console.error('获取建议失败:', error);
    }
  }, []);

  // 处理输入变化
  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);

    // 防抖获取建议
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(() => {
      fetchSuggestions(value);
    }, 300);
  };

  // 选择建议
  const handleSelectSuggestion = (suggestion: Suggestion) => {
    setInput(suggestion.text);
    setShowSuggestions(false);
    textareaRef.current?.focus();
  };

  // 键盘导航
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showSuggestions && suggestions.length > 0) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) =>
            prev < suggestions.length - 1 ? prev + 1 : prev
          );
          return;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => (prev > 0 ? prev - 1 : -1));
          return;
        case 'Tab':
        case 'Enter':
          if (selectedIndex >= 0) {
            e.preventDefault();
            handleSelectSuggestion(suggestions[selectedIndex]);
            return;
          }
          break;
        case 'Escape':
          setShowSuggestions(false);
          return;
      }
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (!input.trim() || isLoading) return;
    onSend(input.trim());
    setInput('');
    setShowSuggestions(false);

    // 重置高度
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      <div className="max-w-4xl mx-auto">
        <div className="relative">
          {/* 搜索建议下拉框 */}
          {showSuggestions && suggestions.length > 0 && (
            <div
              ref={suggestionsRef}
              className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-xl shadow-lg overflow-hidden z-50"
            >
              <div className="px-3 py-2 text-xs text-gray-400 border-b border-gray-100 flex items-center gap-1">
                <Search className="w-3 h-3" />
                <span>搜索建议</span>
              </div>
              {suggestions.map((suggestion, index) => (
                <button
                  key={index}
                  onClick={() => handleSelectSuggestion(suggestion)}
                  className={`w-full px-4 py-2.5 text-left text-sm flex items-center gap-2 transition-colors ${
                    index === selectedIndex
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {suggestion.type === 'document' ? (
                    <FileText className="w-4 h-4 text-blue-500 flex-shrink-0" />
                  ) : (
                    <HelpCircle className="w-4 h-4 text-green-500 flex-shrink-0" />
                  )}
                  <span className="truncate">{suggestion.text}</span>
                </button>
              ))}
            </div>
          )}

          <div className="relative flex items-end gap-2 bg-gray-50 border border-gray-200 rounded-2xl p-2 focus-within:border-primary-300 focus-within:ring-2 focus-within:ring-primary-100 transition-all">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={handleInputChange}
              onKeyDown={handleKeyDown}
              onFocus={() => {
                if (suggestions.length > 0) setShowSuggestions(true);
              }}
              placeholder={placeholder || '输入你的问题，按 Enter 发送，Shift+Enter 换行...'}
              className="flex-1 max-h-[200px] bg-transparent border-0 resize-none px-3 py-2.5 text-gray-700 placeholder-gray-400 focus:outline-none"
              rows={1}
              disabled={isLoading}
            />

            <button
              onClick={handleSubmit}
              disabled={!input.trim() || isLoading}
              className={`flex-shrink-0 p-2.5 rounded-xl transition-all ${
                input.trim() && !isLoading
                  ? 'bg-primary-600 text-white hover:bg-primary-700'
                  : 'bg-gray-200 text-gray-400 cursor-not-allowed'
              }`}
            >
              {isLoading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </div>
        </div>

        <p className="text-xs text-gray-400 mt-2 text-center">
          AI 生成内容仅供参考，请核实重要信息
          {showSuggestions && suggestions.length > 0 && (
            <span className="ml-2 text-gray-300">
              ↑↓ 选择 · Tab/Enter 确认 · Esc 关闭
            </span>
          )}
        </p>
      </div>
    </div>
  );
}
