/**
 * 全局提供者组件
 * 包含主题、字体等全局配置
 */

'use client';

import { ThemeProvider } from '@/components/ThemeProvider';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider>
      {children}
    </ThemeProvider>
  );
}
