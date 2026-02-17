/**
 * 消息列表组件
 * 显示用户和 AI 的对话消息，支持流式输出的打字机效果
 */

import { useRef, useEffect, useState, useMemo, useCallback, memo } from "react";
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

// 使用 memo 减少不必要的重渲染
export const MessageList = memo(function MessageList({
  messages,
}: MessageListProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const lastMessageRef = useRef<HTMLDivElement>(null);
  const [isUserScrolling, setIsUserScrolling] = useState(false);
  const [previewSource, setPreviewSource] = useState<Source | null>(null);

  // 自动滚动到底部 - 仅当用户没有手动滚动时
  useEffect(() => {
    if (lastMessageRef.current && !isUserScrolling) {
      lastMessageRef.current.scrollIntoView({
        behavior: "smooth",
        block: "end",
      });
    }
  }, [messages, isUserScrolling]);

  // 监听用户滚动
  const handleScroll = useCallback(() => {
    console.log("scrolling");
    if (scrollRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
      // 当用户滚动离底部超过 100px 时，标记为用户正在滚动
      setIsUserScrolling(scrollHeight - scrollTop - clientHeight > 100);
    }
  }, []);

  // 为消息生成唯一的key
  const getMessageKey = (message: ChatMessage, index: number): string => {
    // 如果消息有id，使用id，否则使用索引和内容的组合
    if ("id" in message && typeof message.id === "string") {
      return message.id;
    }
    // 使用时间戳和内容的哈希作为唯一标识
    const contentHash = message.content.substring(0, 20) + index;
    return `${message.role}_${contentHash}`;
  };

  // 处理文档预览
  const handlePreview = (source: Source) => {
    setPreviewSource(source);
  };

  // 关闭文档预览
  const handleClosePreview = () => {
    setPreviewSource(null);
  };

  return (
    <div
      ref={scrollRef}
      className="flex-1 min-h-0 h-full overflow-y-auto p-4 space-y-6"
      onScroll={handleScroll}
    >
      {messages.length === 0 && <WelcomeMessage />}

      {messages.map((message, index) => (
        <div
          key={getMessageKey(message, index)}
          ref={index === messages.length - 1 ? lastMessageRef : null}
        >
          <MessageItem message={message} onPreview={handlePreview} />
        </div>
      ))}

      {/* 文档预览 */}
      {previewSource && (
        <DocumentPreview source={previewSource} onClose={handleClosePreview} />
      )}
    </div>
  );
});

// 欢迎消息组件
const WelcomeMessage = memo(function WelcomeMessage() {
  const examples = useMemo(
    () => [
      "Vue3 的 ref 和 reactive 有什么区别？",
      "我们团队的 CSS 命名规范是什么？",
      "React useEffect 的依赖数组怎么写？",
      "TypeScript 的泛型怎么用？",
    ],
    [],
  );

  const handleExampleClick = useCallback((example: string) => {
    const event = new CustomEvent("setInput", { detail: example });
    window.dispatchEvent(event);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center h-full py-12 text-center">
      <div className="w-16 h-16 bg-primary-100 dark:bg-primary-900/30 rounded-2xl flex items-center justify-center mb-6">
        <Bot className="w-8 h-8 text-primary-600 dark:text-primary-400" />
      </div>
      <h2 className="text-2xl font-semibold text-gray-900 dark:text-gray-100 mb-2">
        前端知识库助手
      </h2>
      <p className="text-gray-500 dark:text-gray-400 mb-8 max-w-md">
        我可以帮你查找前端技术知识、公司内部规范和最佳实践。 支持
        React、Vue、TypeScript 等官方文档，以及你们的 GitHub 仓库。
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-lg w-full px-4">
        {examples.map((example, i) => (
          <button
            key={i}
            className="p-3 text-left text-sm text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-primary-300 dark:hover:border-primary-700 hover:bg-primary-50 dark:hover:bg-primary-900/20 transition-colors"
            onClick={() => handleExampleClick(example)}
          >
            {example}
          </button>
        ))}
      </div>
    </div>
  );
});

interface MessageItemProps {
  message: ChatMessage;
  onPreview: (source: Source) => void;
}

// 使用 memo 减少消息项的重渲染
const MessageItem = memo(function MessageItem({
  message,
  onPreview,
}: MessageItemProps) {
  const isUser = message.role === "user";
  const messageRef = useRef<HTMLDivElement>(null);

  const handleHeadingClick = useCallback((headingId: string) => {
    if (messageRef.current) {
      const headingElement = messageRef.current.querySelector(`#${headingId}`);
      if (headingElement) {
        headingElement.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, []);

  return (
    <div
      className={`flex gap-2 sm:gap-4 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
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
      <div
        className={`max-w-[85%] sm:max-w-[80%] ${isUser ? "items-end" : "items-start"}`}
        ref={messageRef}
      >
        {/* 目录导航 - 仅对 AI 消息显示 */}
        {!isUser && !message.isStreaming && (
          <div className="mb-2">
            <TableOfContents content={message.content} onHeadingClick={handleHeadingClick} />
          </div>
        )}

        <div
          className={`px-3 py-2 sm:px-4 sm:py-3 rounded-2xl ${
            isUser
              ? "bg-primary-600 text-white rounded-tr-sm"
              : "bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-tl-sm"
          }`}
        >
          {isUser ? (
            <p className="text-white text-sm sm:text-base">{message.content}</p>
          ) : (
            <div className="markdown text-gray-800 dark:text-gray-200 text-sm sm:text-base">
              <CollapsibleContent
                content={message.content}
                isStreaming={message.isStreaming}
              />
            </div>
          )}
        </div>

        {/* 来源引用 */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
              <BookOpen className="w-3 h-3" />
              <span>参考来源</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, i) => (
                <SourceTag
                  key={`${source.title}_${i}`}
                  source={source}
                  onPreview={onPreview}
                />
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
});

/**
 * 流式内容组件 - 带打字机效果
 */
interface StreamingContentProps {
  content: string;
  isStreaming?: boolean;
}

// 使用 memo 减少重渲染
const StreamingContent = memo(function StreamingContent({
  content,
  isStreaming = false,
}: StreamingContentProps) {
  // 将内容按代码块分割 - 使用 useMemo 缓存结果
  const parts = useMemo(() => {
    return content.split(/(```[\s\S]*?```)/);
  }, [content]);

  // 找到最后一个非代码块的文本部分 - 使用 useMemo 缓存结果
  const lastTextPartIndex = useMemo(() => {
    let index = -1;
    parts.forEach((part, i) => {
      if (!part.startsWith("```")) {
        index = i;
      }
    });
    return index;
  }, [parts]);

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
                key={`code_${index}_${part.length}`}
                language={language || "text"}
                code={code.trim()}
              />
            );
          }
        }

        // 普通文本处理 - 带打字机效果
        const showCursor = isStreaming && index === lastTextPartIndex;

        return (
          <TextPart
            key={`text_${index}`}
            content={part}
            showCursor={showCursor}
          />
        );
      })}
    </>
  );
});

/**
 * 可折叠内容组件
 * 长回答自动折叠，支持展开/收起
 */
interface CollapsibleContentProps {
  content: string;
  isStreaming?: boolean;
  threshold?: number;
}

const CollapsibleContent = memo(function CollapsibleContent({
  content,
  isStreaming = false,
  threshold = 500,
}: CollapsibleContentProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const shouldCollapse = !isStreaming && content.length > threshold;

  const displayContent = shouldCollapse && !isExpanded
    ? content.substring(0, threshold) + "..."
    : content;

  return (
    <div className="relative">
      <StreamingContent content={displayContent} isStreaming={isStreaming} />
      {shouldCollapse && (
        <div className="mt-3">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-sm text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
          >
            {isExpanded ? (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
                </svg>
                收起内容
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
                展开全部 ({Math.ceil((content.length - threshold) / 100) * 100} 字)
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
});

/**
 * 目录导航组件
 * 从内容中提取标题并生成可点击的目录
 */
interface TableOfContentsProps {
  content: string;
  onHeadingClick?: (headingId: string) => void;
}

interface HeadingItem {
  id: string;
  text: string;
  level: number;
}

const TableOfContents = memo(function TableOfContents({
  content,
  onHeadingClick,
}: TableOfContentsProps) {
  const [isOpen, setIsOpen] = useState(false);

  const headings = useMemo(() => {
    const headingRegex = /^(#{1,6})\s+(.+)$/gm;
    const matches: HeadingItem[] = [];
    let match;

    while ((match = headingRegex.exec(content)) !== null) {
      const level = match[1].length;
      const text = match[2].trim();
      const id = `heading-${matches.length}-${text.toLowerCase().replace(/\s+/g, "-")}`;
      matches.push({ id, text, level });
    }

    return matches;
  }, [content]);

  if (headings.length === 0) return null;

  const handleClick = (headingId: string) => {
    onHeadingClick?.(headingId);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1.5 text-xs text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 transition-colors"
        title="目录导航"
      >
        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
        </svg>
        <span>目录 ({headings.length})</span>
      </button>

      {isOpen && (
        <div className="absolute left-0 top-full mt-2 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg z-10 max-h-80 overflow-y-auto">
          <div className="p-3">
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-sm font-medium text-gray-900 dark:text-gray-100">目录导航</h4>
              <button
                onClick={() => setIsOpen(false)}
                className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
            <nav className="space-y-1">
              {headings.map((heading) => (
                <button
                  key={heading.id}
                  onClick={() => handleClick(heading.id)}
                  className={`block w-full text-left text-sm py-1 px-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors ${
                    heading.level === 1
                      ? "font-semibold text-gray-900 dark:text-gray-100"
                      : heading.level === 2
                        ? "pl-4 text-gray-700 dark:text-gray-300"
                        : "pl-6 text-gray-600 dark:text-gray-400"
                  }`}
                >
                  {heading.text}
                </button>
              ))}
            </nav>
          </div>
        </div>
      )}
    </div>
  );
});

/**
 * 代码块组件 - 支持复制功能（整段 + 单行）
 */
interface CodeBlockProps {
  language: string;
  code: string;
}

// 使用 memo 减少重渲染
const CodeBlock = memo(function CodeBlock({ language, code }: CodeBlockProps) {
  const [copiedAll, setCopiedAll] = useState(false);
  const [copiedLine, setCopiedLine] = useState<number | null>(null);
  const [hoveredLine, setHoveredLine] = useState<number | null>(null);

  // 将代码按行分割 - 使用 useMemo 缓存结果
  const lines = useMemo(() => {
    return code.split("\n");
  }, [code]);

  // 复制整段代码
  const handleCopyAll = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedAll(true);
      setTimeout(() => setCopiedAll(false), 2000);
    } catch (err) {
      console.error("复制失败:", err);
    }
  }, [code]);

  // 复制单行代码
  const handleCopyLine = useCallback(
    async (lineContent: string, lineIndex: number) => {
      try {
        await navigator.clipboard.writeText(lineContent);
        setCopiedLine(lineIndex);
        setTimeout(() => setCopiedLine(null), 2000);
      } catch (err) {
        console.error("复制失败:", err);
      }
    },
    [],
  );

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
});

/**
 * 文本部分组件 - 支持打字机效果
 */

interface TextPartProps {
  content: string;
  showCursor: boolean;
}

// 使用 memo 减少重渲染
const TextPart = memo(function TextPart({
  content,
  showCursor,
}: TextPartProps) {
  const [displayedContent, setDisplayedContent] = useState(content);
  const [isTyping, setIsTyping] = useState(showCursor);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    // 清理之前的定时器
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = null;
    }

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

          typingTimeoutRef.current = setTimeout(typeNextChar, delay);
        } else {
          setIsTyping(false);
        }
      };

      typeNextChar();
    }

    // 清理函数
    return () => {
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [content, showCursor, displayedContent.length]);

  // 简单的 Markdown 转换 - 使用 useMemo 缓存结果
  const formatted = useMemo(() => {
    return displayedContent
      .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
      .replace(/\*(.+?)\*/g, "<em>$1</em>")
      .replace(
        /`(.+?)`/g,
        '<code class="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm text-red-600 dark:text-red-400">$1</code>',
      )
      .replace(/\n/g, "<br />");
  }, [displayedContent]);

  return (
    <span className="leading-relaxed inline">
      <span
        className="typing-content"
        dangerouslySetInnerHTML={{ __html: formatted }}
      />
      {(showCursor || isTyping) && <TypingCursor />}
    </span>
  );
});

/**
 * 打字机光标组件
 */
function TypingCursor() {
  return (
    <span className="inline-block w-2 h-5 bg-primary-500 ml-0.5 align-middle animate-pulse rounded-sm" />
  );
}

/**
 * 文档预览组件
 * 点击来源链接时显示文档内容，无需跳转外部网站
 */
interface DocumentPreviewProps {
  source: Source;
  onClose: () => void;
}

const DocumentPreview = memo(function DocumentPreview({
  source,
  onClose,
}: DocumentPreviewProps) {
  const [loading, setLoading] = useState(true);
  const [content, setContent] = useState<string>("");

  useEffect(() => {
    const loadContent = async () => {
      setLoading(true);
      try {
        const docSource = source.url || source.title;
        const response = await fetch(
          `/api/documents/${encodeURIComponent(docSource)}/content`
        );
        if (!response.ok) {
          throw new Error("加载失败");
        }
        const data = await response.json();
        setContent(`# ${data.title}\n\n${data.content}`);
      } catch (error) {
        console.error("加载文档失败:", error);
        setContent("无法加载文档内容，请点击链接在新窗口中查看。");
      } finally {
        setLoading(false);
      }
    };

    loadContent();
  }, [source]);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-2xl w-full max-w-4xl max-h-[80vh] flex flex-col">
        {/* 预览头部 */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
            {source.title}
          </h3>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title="关闭预览"
          >
            <svg
              className="w-5 h-5 text-gray-500 dark:text-gray-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* 预览内容 */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center h-32">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-primary-500"></div>
            </div>
          ) : (
            <div className="prose dark:prose-invert max-w-none">
              <pre className="whitespace-pre-wrap text-sm">{content}</pre>
            </div>
          )}
        </div>

        {/* 预览底部 */}
        <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <span>类型: {source.type}</span>
            {source.url && (
              <a
                href={source.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary-600 dark:text-primary-400 hover:underline flex items-center gap-1"
              >
                在新窗口中打开 <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 dark:bg-gray-700 text-gray-800 dark:text-gray-200 rounded-lg hover:bg-gray-300 dark:hover:bg-gray-600 transition-colors"
          >
            关闭
          </button>
        </div>
      </div>
    </div>
  );
});

interface SourceTagProps {
  source: Source;
  onPreview: (source: Source) => void;
}

const SourceTag = memo(function SourceTag({
  source,
  onPreview,
}: SourceTagProps) {
  const icons = {
    official: Globe,
    github: Github,
    document: FileText,
  };

  const Icon = icons[source.type as keyof typeof icons] || FileText;

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    onPreview(source);
  };

  return (
    <button
      onClick={handleClick}
      className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-full text-xs text-gray-600 dark:text-gray-400 transition-colors cursor-pointer"
      title="点击预览文档"
    >
      <Icon className="w-3 h-3" />
      <span className="truncate max-w-[150px]">{source.title}</span>
      {source.url && <ExternalLink className="w-3 h-3" />}
    </button>
  );
});
