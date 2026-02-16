/**
 * 消息列表组件
 * 显示用户和 AI 的对话消息，支持流式输出的打字机效果
 */

import { useRef, useEffect, useState } from "react";
import { ChatMessage, Source } from "@/lib/api";
import {
  User,
  Bot,
  BookOpen,
  ExternalLink,
  FileText,
  Github,
  Globe,
  Copy,
  Check,
} from "lucide-react";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastMessageRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    if (lastMessageRef.current) {
      lastMessageRef.current.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    }
  }, [messages]);

  return (
    <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-6">
      {messages.length === 0 && <WelcomeMessage />}

      {messages.map((message, index) => (
        <div
          key={index}
          ref={index === messages.length - 1 ? lastMessageRef : null}
        >
          <MessageItem message={message} />
        </div>
      ))}
    </div>
  );
}

function WelcomeMessage() {
  const examples = [
    "Vue3 的 ref 和 reactive 有什么区别？",
    "我们团队的 CSS 命名规范是什么？",
    "React useEffect 的依赖数组怎么写？",
    "TypeScript 的泛型怎么用？",
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full py-12 text-center">
      <div className="w-16 h-16 bg-primary-100 rounded-2xl flex items-center justify-center mb-6">
        <Bot className="w-8 h-8 text-primary-600" />
      </div>
      <h2 className="text-2xl font-semibold text-gray-900 mb-2">
        前端知识库助手
      </h2>
      <p className="text-gray-500 mb-8 max-w-md">
        我可以帮你查找前端技术知识、公司内部规范和最佳实践。 支持
        React、Vue、TypeScript 等官方文档，以及你们的 GitHub 仓库。
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full">
        {examples.map((example, i) => (
          <button
            key={i}
            className="p-3 text-left text-sm text-gray-600 bg-white border border-gray-200 rounded-lg hover:border-primary-300 hover:bg-primary-50 transition-colors"
            onClick={() => {
              const event = new CustomEvent("setInput", { detail: example });
              window.dispatchEvent(event);
            }}
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
}

interface MessageItemProps {
  message: ChatMessage;
}

function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";

  return (
    <div className={`flex gap-2 sm:gap-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}>
      {/* 头像 */}
      <div
        className={`flex-shrink-0 w-8 h-8 sm:w-10 sm:h-10 rounded-full flex items-center justify-center ${
          isUser
            ? "bg-primary-600"
            : "bg-gradient-to-br from-primary-500 to-purple-600"
        }`}
      >
        {isUser ? (
          <User className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
        ) : (
          <Bot className="w-4 h-4 sm:w-5 sm:h-5 text-white" />
        )}
      </div>

      {/* 消息内容 */}
      <div className={`max-w-[85%] sm:max-w-[80%] ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`px-3 py-2 sm:px-4 sm:py-3 rounded-2xl ${
            isUser
              ? "bg-primary-600 text-white rounded-tr-sm"
              : "bg-white border border-gray-200 rounded-tl-sm"
          }`}
        >
          {isUser ? (
            <p className="text-white text-sm sm:text-base">{message.content}</p>
          ) : (
            <div className="markdown text-gray-800 text-sm sm:text-base">
              <StreamingContent
                content={message.content}
                isStreaming={message.isStreaming}
              />
            </div>
          )}
        </div>

        {/* 来源引用 */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-1 text-xs text-gray-500">
              <BookOpen className="w-3 h-3" />
              <span>参考来源</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, i) => (
                <SourceTag key={i} source={source} />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * 流式内容组件 - 带打字机效果
 */
interface StreamingContentProps {
  content: string;
  isStreaming?: boolean;
}

function StreamingContent({ content, isStreaming }: StreamingContentProps) {
  // 将内容按代码块分割
  const parts = content.split(/(```[\s\S]*?```)/);
  // 找到最后一个非代码块的文本部分
  let lastTextPartIndex = -1;
  parts.forEach((part, index) => {
    if (!part.startsWith("```")) {
      lastTextPartIndex = index;
    }
  });

  return (
    <>
      {parts.map((part, index) => {
        // 代码块处理
        if (part.startsWith("```") && part.endsWith("```")) {
          const match = part.match(/```(\w+)?\n?([\s\S]*?)```/);
          if (match) {
            const [, language, code] = match;
            return (
              <CodeBlock
                key={index}
                language={language || "text"}
                code={code.trim()}
              />
            );
          }
        }

        // 普通文本处理 - 带打字机效果
        const showCursor = isStreaming && index === lastTextPartIndex;

        return <TextPart key={index} content={part} showCursor={showCursor} />;
      })}
    </>
  );
}

/**
 * 代码块组件 - 支持复制功能（整段 + 单行）
 */
interface CodeBlockProps {
  language: string;
  code: string;
}

function CodeBlock({ language, code }: CodeBlockProps) {
  const [copiedAll, setCopiedAll] = useState(false);
  const [copiedLine, setCopiedLine] = useState<number | null>(null);
  const [hoveredLine, setHoveredLine] = useState<number | null>(null);

  // 复制整段代码
  const handleCopyAll = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch (err) {
      console.error("复制失败:", err);
    }
  };

  // 复制单行代码
  const handleCopyLine = async (lineContent: string, lineIndex: number) => {
    try {
      await navigator.clipboard.writeText(lineContent);
      setCopiedLine(lineIndex);
      setTimeout(() => setCopiedLine(null), 2000);
    } catch (err) {
      console.error("复制失败:", err);
    }
  };

  // 将代码按行分割
  const lines = code.split("\n");

  return (
    <div className="my-3 relative group rounded-lg overflow-hidden bg-gray-900">
      {/* 代码块头部 - 始终显示 */}
      <div className="flex items-center justify-between text-xs text-gray-400 bg-gray-800 px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="font-medium">{language}</span>
          <span className="text-gray-500">·</span>
          <span className="text-gray-500">{lines.length} 行</span>
        </div>
        <button
          onClick={handleCopyAll}
          className="flex items-center gap-1.5 px-2 py-1 rounded hover:bg-gray-700 transition-all"
          title="复制全部代码"
        >
          {copiedAll ? (
            <>
              <Check className="w-3.5 h-3.5 text-green-400" />
              <span className="text-green-400">已复制全部</span>
            </>
          ) : (
            <>
              <Copy className="w-3.5 h-3.5" />
              <span>复制全部</span>
            </>
          )}
        </button>
      </div>

      {/* 代码内容 - 带行号和单行复制 */}
      <div className="relative overflow-x-auto">
        <div className="flex text-sm leading-relaxed">
          {/* 行号栏 */}
          <div className="flex-shrink-0 bg-gray-800 text-gray-500 text-right select-none">
            {lines.map((_, index) => (
              <div
                key={index}
                className="px-3 py-0.5 relative group/line"
                onMouseEnter={() => setHoveredLine(index)}
                onMouseLeave={() => setHoveredLine(null)}
              >
                {/* 行号 */}
                <span className={hoveredLine === index ? "text-gray-300" : ""}>
                  {index + 1}
                </span>

                {/* 单行复制按钮 - 悬停时显示 */}
                {hoveredLine === index && (
                  <button
                    onClick={() => handleCopyLine(lines[index], index)}
                    className="absolute right-full top-1/2 -translate-y-1/2 mr-1 p-1 rounded bg-gray-700 text-gray-300 hover:text-white opacity-0 group-hover/line:opacity-100 transition-opacity"
                    title={`复制第 ${index + 1} 行`}
                  >
                    {copiedLine === index ? (
                      <Check className="w-3 h-3 text-green-400" />
                    ) : (
                      <Copy className="w-3 h-3" />
                    )}
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* 代码内容 */}
          <div className="flex-1 bg-gray-900 text-gray-100">
            {lines.map((line, index) => (
              <div
                key={index}
                className={`px-4 py-0.5 whitespace-pre ${
                  hoveredLine === index ? "bg-gray-800/50" : ""
                }`}
                onMouseEnter={() => setHoveredLine(index)}
                onMouseLeave={() => setHoveredLine(null)}
                onClick={() => handleCopyLine(line, index)}
                title="点击复制该行"
              >
                <code>{line || " "}</code>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * 文本部分组件 - 支持打字机效果
 */
function TextPart({
  content,
  showCursor,
}: {
  content: string;
  showCursor: boolean;
}) {
  const [displayedContent, setDisplayedContent] = useState(content);
  const [isTyping, setIsTyping] = useState(showCursor);

  useEffect(() => {
    // 如果不在流式状态，直接显示完整内容
    if (!showCursor) {
      setDisplayedContent(content);
      setIsTyping(false);
      return;
    }

    // 流式状态下，如果内容增加了，启动逐字动画
    if (content.length > displayedContent.length) {
      setIsTyping(true);
      const targetText = content;
      let currentIndex = displayedContent.length;

      const typeNextChar = () => {
        if (currentIndex < targetText.length) {
          // 每次显示 1-2 个字符，模拟打字速度
          const chunkSize = Math.floor(Math.random() * 2) + 1;
          currentIndex = Math.min(currentIndex + chunkSize, targetText.length);
          setDisplayedContent(targetText.slice(0, currentIndex));

          // 根据字符类型调整延迟
          const char = targetText[currentIndex - 1];
          let delay = 15; // 基础延迟 15ms

          if (char === " ") {
            delay = 30; // 空格和换行稍慢
          } else if (`，。！？；：""''（）`.includes(char)) {
            delay = 80; // 标点符号停顿一下
          } else if (`,.!?;:()""''`.includes(char)) {
            delay = 60; // 英文标点
          }

          setTimeout(typeNextChar, delay);
        } else {
          setIsTyping(false);
        }
      };

      typeNextChar();
    }
  }, [content, showCursor]);

  // 简单的 Markdown 转换
  const formatted = displayedContent
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(
      /`(.+?)`/g,
      '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm text-red-600">$1</code>',
    )
    .replace(/\n/g, "<br />");

  return (
    <span className="leading-relaxed inline">
      <span
        className="typing-content"
        dangerouslySetInnerHTML={{ __html: formatted }}
      />
      {(showCursor || isTyping) && <TypingCursor />}
    </span>
  );
}

/**
 * 打字机光标组件
 */
function TypingCursor() {
  return (
    <span className="inline-block w-2 h-5 bg-primary-500 ml-0.5 align-middle animate-pulse rounded-sm" />
  );
}

function SourceTag({ source }: { source: Source }) {
  const icons = {
    official: Globe,
    github: Github,
    document: FileText,
  };

  const Icon = icons[source.type as keyof typeof icons] || FileText;

  return (
    <a
      href={source.url || "#"}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 hover:bg-gray-200 rounded-full text-xs text-gray-600 transition-colors"
    >
      <Icon className="w-3 h-3" />
      <span className="truncate max-w-[150px]">{source.title}</span>
      {source.url && <ExternalLink className="w-3 h-3" />}
    </a>
  );
}
