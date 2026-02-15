import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: '前端知识库 - AI 问答助手',
  description: '基于 RAG 的前端开发知识库，帮助团队快速查找技术知识和规范',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="zh-CN">
      <body className="antialiased">{children}</body>
    </html>
  );
}
