/**
 * 主题切换按钮组件
 * 支持浅色/深色/系统主题切换
 */

import { Sun, Moon, Monitor } from "lucide-react";
import { useTheme } from "./ThemeProvider";
import { useState, useRef, useEffect } from "react";

export function ThemeToggle() {
  const { theme, setTheme, resolvedTheme, toggleTheme } = useTheme();
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowMenu(false);
      }
    };

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const themeOptions = [
    { value: "light" as const, label: "浅色", icon: Sun },
    { value: "dark" as const, label: "深色", icon: Moon },
    { value: "system" as const, label: "跟随系统", icon: Monitor },
  ];

  return (
    <div className="relative" ref={menuRef}>
      {/* 切换按钮 */}
      <button
        onClick={() => setShowMenu(!showMenu)}
        className="p-2 rounded-lg text-gray-600 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800 transition-colors"
        title={`当前主题: ${theme === "system" ? "跟随系统" : theme === "dark" ? "深色" : "浅色"}`}
      >
        {resolvedTheme === "dark" ? (
          <Moon className="w-5 h-5" />
        ) : (
          <Sun className="w-5 h-5" />
        )}
      </button>

      {/* 主题选择菜单 */}
      {showMenu && (
        <div className="absolute right-0 top-full mt-2 w-40 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg overflow-hidden z-50">
          {themeOptions.map((option) => {
            const Icon = option.icon;
            const isActive = theme === option.value;

            return (
              <button
                key={option.value}
                onClick={() => {
                  setTheme(option.value);
                  setShowMenu(false);
                }}
                className={`w-full px-4 py-2.5 text-sm flex items-center gap-2 transition-colors ${
                  isActive
                    ? "bg-primary-50 text-primary-700 dark:bg-primary-900/30 dark:text-primary-400"
                    : "text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span>{option.label}</span>
                {isActive && <span className="ml-auto text-xs">✓</span>}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
