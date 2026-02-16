"""
社区贡献模块
支持提示词分享、知识库配置、最佳实践案例库
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional
from config import BASE_DIR

COMMUNITY_DB_PATH = BASE_DIR / "community.db"


class CommunityManager:
    """社区管理器"""

    def __init__(self):
        self.db_path = COMMUNITY_DB_PATH
        self._init_db()
        self._init_default_content()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    tags TEXT,
                    likes INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    is_featured BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT NOT NULL,
                    description TEXT,
                    config_json TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    downloads INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS best_practices (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    description TEXT,
                    content TEXT NOT NULL,
                    category TEXT DEFAULT 'general',
                    tags TEXT,
                    difficulty INTEGER DEFAULT 1,
                    likes INTEGER DEFAULT 0,
                    views INTEGER DEFAULT 0,
                    is_featured BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS community_likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    item_type TEXT NOT NULL,
                    item_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_type, item_id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompts_category
                ON prompts(category)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_configs_category
                ON knowledge_configs(category)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_practices_category
                ON best_practices(category)
            """)

            conn.commit()

    def _init_default_content(self):
        """初始化默认内容"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM prompts")
            if cursor.fetchone()[0] > 0:
                return

            prompts = [
                ("代码解释专家", "让 AI 详细解释代码的工作原理", "请详细解释以下代码的工作原理，包括每个函数的作用、参数含义和返回值：\n\n{code}\n\n请用简单易懂的语言解释，并指出潜在的优化点。", "code", "代码,解释,优化"),
                ("Bug 调试助手", "帮助定位和修复代码中的 Bug", "我在以下代码中遇到了问题：\n\n{code}\n\n错误信息是：{error}\n\n请帮我分析可能的原因并提供修复建议。", "debug", "调试,Bug,错误"),
                ("代码审查专家", "对代码进行专业审查", "请对以下代码进行专业审查，关注以下方面：\n1. 代码质量和可读性\n2. 性能优化建议\n3. 安全性问题\n4. 最佳实践建议\n\n代码：\n{code}", "review", "代码审查,优化,安全"),
                ("技术文档生成器", "自动生成技术文档", "请为以下代码生成详细的技术文档，包括：\n1. 功能描述\n2. 参数说明\n3. 返回值说明\n4. 使用示例\n5. 注意事项\n\n代码：\n{code}", "docs", "文档,注释,说明"),
                ("学习路径规划师", "规划技术学习路径", "我想学习 {topic}，请为我制定一个详细的学习路径，包括：\n1. 学习阶段划分\n2. 每个阶段的学习重点\n3. 推荐的学习资源\n4. 实践项目建议", "learning", "学习,路径,规划"),
            ]

            for title, desc, content, category, tags in prompts:
                cursor.execute(
                    """
                    INSERT INTO prompts (title, description, content, category, tags)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (title, desc, content, category, tags)
                )

            configs = [
                ("Vue3 基础知识库", "包含 Vue3 核心概念的文档配置", json.dumps({
                    "sources": [
                        {"type": "official", "url": "https://vuejs.org/guide/introduction.html"},
                        {"type": "official", "url": "https://vuejs.org/api/"}
                    ],
                    "settings": {"chunk_size": 500, "overlap": 50}
                }), "Vue"),
                ("React Hooks 知识库", "React Hooks 完整文档配置", json.dumps({
                    "sources": [
                        {"type": "official", "url": "https://react.dev/reference/react"}
                    ],
                    "settings": {"chunk_size": 500, "overlap": 50}
                }), "React"),
                ("TypeScript 入门配置", "TypeScript 基础知识库配置", json.dumps({
                    "sources": [
                        {"type": "official", "url": "https://www.typescriptlang.org/docs/handbook/"}
                    ],
                    "settings": {"chunk_size": 600, "overlap": 100}
                }), "TypeScript"),
            ]

            for name, desc, config, category in configs:
                cursor.execute(
                    """
                    INSERT INTO knowledge_configs (name, description, config_json, category)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, desc, config, category)
                )

            practices = [
                ("Vue 组件设计原则", "Vue 组件设计的最佳实践", """
## Vue 组件设计原则

### 1. 单一职责原则
每个组件应该只负责一件事情，这样可以使组件更易于理解、测试和维护。

### 2. Props Down, Events Up
- 父组件通过 props 向子组件传递数据
- 子组件通过 events 向父组件传递消息
- 避免直接修改 props

### 3. 合理使用 computed 和 watch
- computed 用于派生状态
- watch 用于副作用操作

### 4. 组件命名规范
- 使用 PascalCase 命名组件
- 组件名应该是多个单词
- 使用有意义的名称

### 5. 避免 v-if 和 v-for 同时使用
```vue
<!-- 不推荐 -->
<div v-for="item in items" v-if="item.isActive">

<!-- 推荐 -->
<template v-for="item in items">
  <div v-if="item.isActive">
</template>
```
                """, "Vue", "组件,设计,最佳实践", 2),
                ("React 性能优化指南", "React 应用性能优化技巧", """
## React 性能优化指南

### 1. 使用 React.memo
避免不必要的组件重渲染：
```jsx
const MyComponent = React.memo(function MyComponent(props) {
  // ...
});
```

### 2. 合理使用 useMemo 和 useCallback
- useMemo 缓存计算结果
- useCallback 缓存回调函数

### 3. 虚拟列表
对于长列表，使用 react-window 或 react-virtualized：
```jsx
import { FixedSizeList } from 'react-window';

<FixedSizeList
  height={600}
  itemCount={1000}
  itemSize={35}
>
  {Row}
</FixedSizeList>
```

### 4. 代码分割
使用 React.lazy 和 Suspense：
```jsx
const LazyComponent = React.lazy(() => import('./LazyComponent'));

<Suspense fallback={<Loading />}>
  <LazyComponent />
</Suspense>
```

### 5. 避免内联函数和对象
在渲染方法中避免创建新的函数和对象。
                """, "React", "性能,优化,React", 3),
                ("TypeScript 类型技巧", "TypeScript 高级类型使用技巧", """
## TypeScript 类型技巧

### 1. 使用类型推断
让 TypeScript 自动推断类型，减少显式类型注解：
```typescript
// 不推荐
const name: string = 'John';

// 推荐
const name = 'John';
```

### 2. 使用 const assertions
```typescript
const config = {
  endpoint: '/api'
} as const;
```

### 3. 工具类型
```typescript
// Partial - 所有属性可选
type PartialUser = Partial<User>;

// Pick - 选择部分属性
type UserPreview = Pick<User, 'id' | 'name'>;

// Omit - 排除部分属性
type UserWithoutPassword = Omit<User, 'password'>;
```

### 4. 泛型约束
```typescript
function getProperty<T, K extends keyof T>(obj: T, key: K): T[K] {
  return obj[key];
}
```

### 5. 条件类型
```typescript
type NonNullable<T> = T extends null | undefined ? never : T;
```
                """, "TypeScript", "类型,技巧,高级", 3),
            ]

            for title, desc, content, category, tags, difficulty in practices:
                cursor.execute(
                    """
                    INSERT INTO best_practices (title, description, content, category, tags, difficulty)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (title, desc, content, category, tags, difficulty)
                )

            conn.commit()

    def share_prompt(
        self,
        user_id: int,
        title: str,
        content: str,
        description: str = None,
        category: str = "general",
        tags: str = None
    ) -> Dict:
        """分享提示词"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO prompts (user_id, title, description, content, category, tags)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, title, description, content, category, tags)
            )

            conn.commit()

            return {
                "id": cursor.lastrowid,
                "title": title,
                "category": category,
                "created_at": datetime.now().isoformat()
            }

    def get_prompts(
        self,
        category: str = None,
        search: str = None,
        sort_by: str = "created_at",
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict]:
        """获取提示词列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM prompts WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)

            if search:
                query += " AND (title LIKE ? OR description LIKE ? OR tags LIKE ?)"
                search_term = f"%{search}%"
                params.extend([search_term, search_term, search_term])

            if sort_by == "likes":
                query += " ORDER BY likes DESC, created_at DESC"
            elif sort_by == "views":
                query += " ORDER BY views DESC, created_at DESC"
            else:
                query += " ORDER BY created_at DESC"

            query += " LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(query, params)

            return [dict(row) for row in cursor.fetchall()]

    def get_prompt(self, prompt_id: int) -> Optional[Dict]:
        """获取提示词详情"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE prompts SET views = views + 1 WHERE id = ?",
                (prompt_id,)
            )

            cursor.execute("SELECT * FROM prompts WHERE id = ?", (prompt_id,))
            row = cursor.fetchone()

            if row:
                conn.commit()
                return dict(row)
            return None

    def share_config(
        self,
        user_id: int,
        name: str,
        config_json: str,
        description: str = None,
        category: str = "general"
    ) -> Dict:
        """分享知识库配置"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO knowledge_configs (user_id, name, description, config_json, category)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, name, description, config_json, category)
            )

            conn.commit()

            return {
                "id": cursor.lastrowid,
                "name": name,
                "category": category
            }

    def get_configs(
        self,
        category: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """获取知识库配置列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if category:
                cursor.execute(
                    """
                    SELECT id, name, description, category, downloads, likes, created_at
                    FROM knowledge_configs
                    WHERE category = ?
                    ORDER BY downloads DESC, created_at DESC
                    LIMIT ?
                    """,
                    (category, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, name, description, category, downloads, likes, created_at
                    FROM knowledge_configs
                    ORDER BY downloads DESC, created_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                )

            return [dict(row) for row in cursor.fetchall()]

    def get_config(self, config_id: int) -> Optional[Dict]:
        """获取知识库配置详情"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE knowledge_configs SET downloads = downloads + 1 WHERE id = ?",
                (config_id,)
            )

            cursor.execute("SELECT * FROM knowledge_configs WHERE id = ?", (config_id,))
            row = cursor.fetchone()

            if row:
                conn.commit()
                return dict(row)
            return None

    def share_practice(
        self,
        user_id: int,
        title: str,
        content: str,
        description: str = None,
        category: str = "general",
        tags: str = None,
        difficulty: int = 1
    ) -> Dict:
        """分享最佳实践"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO best_practices (user_id, title, description, content, category, tags, difficulty)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, title, description, content, category, tags, difficulty)
            )

            conn.commit()

            return {
                "id": cursor.lastrowid,
                "title": title,
                "category": category
            }

    def get_practices(
        self,
        category: str = None,
        difficulty: int = None,
        limit: int = 20
    ) -> List[Dict]:
        """获取最佳实践列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM best_practices WHERE 1=1"
            params = []

            if category:
                query += " AND category = ?"
                params.append(category)

            if difficulty:
                query += " AND difficulty = ?"
                params.append(difficulty)

            query += " ORDER BY likes DESC, created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            return [dict(row) for row in cursor.fetchall()]

    def get_practice(self, practice_id: int) -> Optional[Dict]:
        """获取最佳实践详情"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE best_practices SET views = views + 1 WHERE id = ?",
                (practice_id,)
            )

            cursor.execute("SELECT * FROM best_practices WHERE id = ?", (practice_id,))
            row = cursor.fetchone()

            if row:
                conn.commit()
                return dict(row)
            return None

    def like_item(
        self,
        user_id: int,
        item_type: str,
        item_id: int
    ) -> Dict:
        """点赞"""
        valid_types = ["prompt", "config", "practice"]
        if item_type not in valid_types:
            raise ValueError(f"无效的类型: {item_type}")

        table_map = {
            "prompt": "prompts",
            "config": "knowledge_configs",
            "practice": "best_practices"
        }

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id FROM community_likes
                WHERE user_id = ? AND item_type = ? AND item_id = ?
                """,
                (user_id, item_type, item_id)
            )

            existing = cursor.fetchone()

            if existing:
                cursor.execute(
                    "DELETE FROM community_likes WHERE id = ?",
                    (existing[0],)
                )
                cursor.execute(
                    f"UPDATE {table_map[item_type]} SET likes = likes - 1 WHERE id = ?",
                    (item_id,)
                )
                action = "unliked"
            else:
                cursor.execute(
                    """
                    INSERT INTO community_likes (user_id, item_type, item_id)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, item_type, item_id)
                )
                cursor.execute(
                    f"UPDATE {table_map[item_type]} SET likes = likes + 1 WHERE id = ?",
                    (item_id,)
                )
                action = "liked"

            conn.commit()

            return {"action": action, "item_type": item_type, "item_id": item_id}

    def get_categories(self) -> Dict:
        """获取所有类别"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT DISTINCT category FROM prompts")
            prompt_categories = [row[0] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT category FROM knowledge_configs")
            config_categories = [row[0] for row in cursor.fetchall()]

            cursor.execute("SELECT DISTINCT category FROM best_practices")
            practice_categories = [row[0] for row in cursor.fetchall()]

            return {
                "prompts": prompt_categories,
                "configs": config_categories,
                "practices": practice_categories
            }


_community_manager = None


def get_community_manager() -> CommunityManager:
    """获取社区管理器单例"""
    global _community_manager
    if _community_manager is None:
        _community_manager = CommunityManager()
    return _community_manager
