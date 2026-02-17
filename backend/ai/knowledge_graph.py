"""
知识图谱模块
构建前端技术知识图谱，支持可视化关联和学习路径推荐
"""
import sqlite3
import json
from typing import List, Dict, Optional, Set
from collections import defaultdict
from config import AI_DB_PATH


class KnowledgeGraph:
    """知识图谱"""

    def __init__(self):
        self.db_path = AI_DB_PATH
        self._init_db()
        self._init_default_data()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_nodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    category TEXT NOT NULL,
                    description TEXT,
                    difficulty INTEGER DEFAULT 1,
                    importance INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS knowledge_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    target_id INTEGER NOT NULL,
                    relation_type TEXT NOT NULL,
                    weight REAL DEFAULT 1.0,
                    FOREIGN KEY (source_id) REFERENCES knowledge_nodes(id),
                    FOREIGN KEY (target_id) REFERENCES knowledge_nodes(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_paths (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    nodes TEXT NOT NULL,
                    difficulty INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_nodes_category
                ON knowledge_nodes(category)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_relations_source
                ON knowledge_relations(source_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_relations_target
                ON knowledge_relations(target_id)
            """)

            conn.commit()

    def _init_default_data(self):
        """初始化默认知识图谱数据"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM knowledge_nodes")
            if cursor.fetchone()[0] > 0:
                return

            nodes = [
                ("JavaScript", "language", "Web 开发的核心语言", 1, 5),
                ("TypeScript", "language", "JavaScript 的超集，添加类型系统", 2, 5),
                ("Vue", "framework", "渐进式 JavaScript 框架", 2, 5),
                ("React", "framework", "用于构建用户界面的 JavaScript 库", 2, 5),
                ("Angular", "framework", "企业级前端框架", 3, 4),
                ("HTML", "language", "超文本标记语言", 1, 5),
                ("CSS", "language", "层叠样式表", 1, 5),
                ("Flexbox", "layout", "弹性盒子布局", 1, 4),
                ("Grid", "layout", "网格布局", 2, 4),
                ("ES6", "language", "ECMAScript 2015+ 新特性", 2, 5),
                ("Promise", "concept", "异步编程解决方案", 2, 5),
                ("Async/Await", "concept", "Promise 的语法糖", 2, 5),
                ("组件化", "concept", "前端架构思想", 2, 5),
                ("状态管理", "concept", "应用状态管理方案", 3, 4),
                ("Vuex", "library", "Vue 状态管理模式", 3, 4),
                ("Pinia", "library", "Vue 新一代状态管理", 3, 4),
                ("Redux", "library", "React 状态管理库", 3, 4),
                ("Vue Router", "library", "Vue 官方路由", 2, 4),
                ("React Router", "library", "React 路由库", 2, 4),
                ("Webpack", "tool", "模块打包工具", 3, 4),
                ("Vite", "tool", "下一代前端构建工具", 2, 5),
                ("Node.js", "runtime", "JavaScript 运行时", 2, 4),
                ("npm", "tool", "Node 包管理器", 1, 4),
                ("pnpm", "tool", "高效的包管理器", 2, 3),
                ("单元测试", "testing", "模块级别测试", 3, 4),
                ("E2E测试", "testing", "端到端测试", 3, 3),
                ("性能优化", "concept", "前端性能优化技术", 3, 5),
                ("懒加载", "technique", "按需加载资源", 2, 4),
                ("虚拟DOM", "concept", "轻量级 DOM 表示", 3, 4),
                ("SSR", "technique", "服务端渲染", 4, 4),
                ("SSG", "technique", "静态站点生成", 3, 3),
                ("微前端", "architecture", "前端微服务架构", 4, 3),
                ("响应式", "concept", "数据驱动视图更新", 2, 5),
                ("Composition API", "api", "Vue3 组合式 API", 3, 5),
                ("Hooks", "api", "React Hooks", 3, 5),
                ("TypeScript类型", "concept", "TS 类型系统", 3, 5),
            ]

            for node in nodes:
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO knowledge_nodes
                    (name, category, description, difficulty, importance)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    node
                )

            conn.commit()

            cursor.execute("SELECT id, name FROM knowledge_nodes")
            name_to_id = {row[1]: row[0] for row in cursor.fetchall()}

            relations = [
                ("JavaScript", "TypeScript", "prerequisite", 1.0),
                ("JavaScript", "Vue", "prerequisite", 1.0),
                ("JavaScript", "React", "prerequisite", 1.0),
                ("JavaScript", "Angular", "prerequisite", 1.0),
                ("JavaScript", "Node.js", "prerequisite", 1.0),
                ("JavaScript", "ES6", "includes", 1.0),
                ("ES6", "Promise", "includes", 1.0),
                ("Promise", "Async/Await", "related", 0.9),
                ("HTML", "CSS", "related", 0.8),
                ("CSS", "Flexbox", "includes", 1.0),
                ("CSS", "Grid", "includes", 1.0),
                ("Vue", "Vuex", "uses", 0.9),
                ("Vue", "Pinia", "uses", 0.9),
                ("Vue", "Vue Router", "uses", 1.0),
                ("Vue", "Composition API", "includes", 1.0),
                ("Vue", "响应式", "implements", 1.0),
                ("Vue", "虚拟DOM", "uses", 0.8),
                ("React", "Redux", "uses", 0.9),
                ("React", "React Router", "uses", 1.0),
                ("React", "Hooks", "includes", 1.0),
                ("React", "虚拟DOM", "uses", 1.0),
                ("TypeScript", "TypeScript类型", "includes", 1.0),
                ("组件化", "Vue", "implemented_by", 0.9),
                ("组件化", "React", "implemented_by", 0.9),
                ("状态管理", "Vuex", "implemented_by", 0.8),
                ("状态管理", "Pinia", "implemented_by", 0.9),
                ("状态管理", "Redux", "implemented_by", 0.8),
                ("Node.js", "npm", "includes", 1.0),
                ("Webpack", "Vite", "alternative", 0.7),
                ("性能优化", "懒加载", "uses", 0.9),
                ("性能优化", "SSR", "uses", 0.8),
                ("单元测试", "Vue", "tests", 0.7),
                ("单元测试", "React", "tests", 0.7),
            ]

            for source, target, rel_type, weight in relations:
                source_id = name_to_id.get(source)
                target_id = name_to_id.get(target)
                if source_id and target_id:
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO knowledge_relations
                        (source_id, target_id, relation_type, weight)
                        VALUES (?, ?, ?, ?)
                        """,
                        (source_id, target_id, rel_type, weight)
                    )

            conn.commit()

            paths = [
                ("前端入门路径", "从零开始学习前端开发", ["HTML", "CSS", "JavaScript", "ES6"], 1),
                ("Vue 开发者路径", "成为 Vue 开发者", ["JavaScript", "ES6", "Vue", "Vue Router", "Pinia"], 2),
                ("React 开发者路径", "成为 React 开发者", ["JavaScript", "ES6", "React", "Hooks", "Redux"], 2),
                ("TypeScript 进阶路径", "掌握 TypeScript", ["JavaScript", "TypeScript", "TypeScript类型"], 3),
                ("前端架构师路径", "进阶前端架构", ["Vue", "React", "性能优化", "SSR", "微前端"], 4),
            ]

            for name, desc, nodes_list, diff in paths:
                cursor.execute(
                    """
                    INSERT INTO learning_paths (name, description, nodes, difficulty)
                    VALUES (?, ?, ?, ?)
                    """,
                    (name, desc, json.dumps(nodes_list), diff)
                )

            conn.commit()

    def get_all_nodes(self) -> List[Dict]:
        """获取所有知识节点"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT id, name, category, description, difficulty, importance
                FROM knowledge_nodes
                ORDER BY importance DESC, name
            """)

            return [dict(row) for row in cursor.fetchall()]

    def get_nodes_by_category(self, category: str) -> List[Dict]:
        """按类别获取节点"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, name, category, description, difficulty, importance
                FROM knowledge_nodes
                WHERE category = ?
                ORDER BY importance DESC
                """,
                (category,)
            )

            return [dict(row) for row in cursor.fetchall()]

    def get_node_detail(self, node_id: int) -> Optional[Dict]:
        """获取节点详情"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, name, category, description, difficulty, importance
                FROM knowledge_nodes
                WHERE id = ?
                """,
                (node_id,)
            )

            row = cursor.fetchone()
            if not row:
                return None

            node = dict(row)

            cursor.execute(
                """
                SELECT n.id, n.name, n.category, r.relation_type, r.weight
                FROM knowledge_relations r
                JOIN knowledge_nodes n ON r.target_id = n.id
                WHERE r.source_id = ?
                """,
                (node_id,)
            )
            node["outgoing_relations"] = [dict(r) for r in cursor.fetchall()]

            cursor.execute(
                """
                SELECT n.id, n.name, n.category, r.relation_type, r.weight
                FROM knowledge_relations r
                JOIN knowledge_nodes n ON r.source_id = n.id
                WHERE r.target_id = ?
                """,
                (node_id,)
            )
            node["incoming_relations"] = [dict(r) for r in cursor.fetchall()]

            return node

    def get_all_relations(self) -> List[Dict]:
        """获取所有关系"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("""
                SELECT
                    r.id, r.relation_type, r.weight,
                    s.name as source_name, s.id as source_id,
                    t.name as target_name, t.id as target_id
                FROM knowledge_relations r
                JOIN knowledge_nodes s ON r.source_id = s.id
                JOIN knowledge_nodes t ON r.target_id = t.id
            """)

            return [dict(row) for row in cursor.fetchall()]

    def get_graph_data(self) -> Dict:
        """获取图谱可视化数据"""
        nodes = self.get_all_nodes()
        relations = self.get_all_relations()

        return {
            "nodes": [
                {
                    "id": n["id"],
                    "name": n["name"],
                    "category": n["category"],
                    "difficulty": n["difficulty"],
                    "importance": n["importance"]
                }
                for n in nodes
            ],
            "links": [
                {
                    "source": r["source_id"],
                    "target": r["target_id"],
                    "type": r["relation_type"],
                    "weight": r["weight"]
                }
                for r in relations
            ]
        }

    def get_categories(self) -> List[str]:
        """获取所有类别"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT DISTINCT category FROM knowledge_nodes ORDER BY category"
            )

            return [row[0] for row in cursor.fetchall()]

    def get_learning_paths(self, difficulty: int = None) -> List[Dict]:
        """获取学习路径"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if difficulty:
                cursor.execute(
                    """
                    SELECT id, name, description, nodes, difficulty
                    FROM learning_paths
                    WHERE difficulty <= ?
                    ORDER BY difficulty
                    """,
                    (difficulty,)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, name, description, nodes, difficulty
                    FROM learning_paths
                    ORDER BY difficulty
                    """
                )

            paths = []
            for row in cursor.fetchall():
                path = dict(row)
                path["nodes"] = json.loads(path["nodes"])
                paths.append(path)

            return paths

    def recommend_path(self, known_nodes: List[str]) -> Dict:
        """推荐学习路径"""
        all_nodes = {n["name"]: n for n in self.get_all_nodes()}

        known_set = set(known_nodes)

        candidates = []
        for name, node in all_nodes.items():
            if name not in known_set:
                cursor = sqlite3.connect(self.db_path).cursor()
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM knowledge_relations
                    WHERE target_id = (SELECT id FROM knowledge_nodes WHERE name = ?)
                    AND relation_type = 'prerequisite'
                    """,
                    (name,)
                )
                prereq_count = cursor.fetchone()[0]

                cursor.execute(
                    """
                    SELECT s.name FROM knowledge_relations r
                    JOIN knowledge_nodes s ON r.source_id = s.id
                    WHERE r.target_id = (SELECT id FROM knowledge_nodes WHERE name = ?)
                    AND r.relation_type = 'prerequisite'
                    """,
                    (name,)
                )
                prereqs = [row[0] for row in cursor.fetchall()]

                prereqs_met = all(p in known_set for p in prereqs)

                if prereqs_met or prereq_count == 0:
                    candidates.append({
                        "name": name,
                        "difficulty": node["difficulty"],
                        "importance": node["importance"],
                        "prerequisites_met": prereqs_met
                    })

        candidates.sort(key=lambda x: (-x["importance"], x["difficulty"]))

        return {
            "known_nodes": known_nodes,
            "recommended_next": candidates[:5],
            "total_candidates": len(candidates)
        }

    def search_nodes(self, query: str) -> List[Dict]:
        """搜索知识节点"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, name, category, description, difficulty, importance
                FROM knowledge_nodes
                WHERE name LIKE ? OR description LIKE ?
                ORDER BY importance DESC
                LIMIT 20
                """,
                (f'%{query}%', f'%{query}%')
            )

            return [dict(row) for row in cursor.fetchall()]

    def add_node(
        self,
        name: str,
        category: str,
        description: str = None,
        difficulty: int = 1,
        importance: int = 1
    ) -> Dict:
        """添加知识节点"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO knowledge_nodes (name, category, description, difficulty, importance)
                VALUES (?, ?, ?, ?, ?)
                """,
                (name, category, description, difficulty, importance)
            )

            conn.commit()

            return {
                "id": cursor.lastrowid,
                "name": name,
                "category": category
            }

    def add_relation(
        self,
        source_name: str,
        target_name: str,
        relation_type: str,
        weight: float = 1.0
    ) -> bool:
        """添加知识关系"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "SELECT id FROM knowledge_nodes WHERE name = ?",
                (source_name,)
            )
            source = cursor.fetchone()
            if not source:
                return False

            cursor.execute(
                "SELECT id FROM knowledge_nodes WHERE name = ?",
                (target_name,)
            )
            target = cursor.fetchone()
            if not target:
                return False

            cursor.execute(
                """
                INSERT OR REPLACE INTO knowledge_relations
                (source_id, target_id, relation_type, weight)
                VALUES (?, ?, ?, ?)
                """,
                (source[0], target[0], relation_type, weight)
            )

            conn.commit()
            return True


_knowledge_graph = None


def get_knowledge_graph() -> KnowledgeGraph:
    """获取知识图谱单例"""
    global _knowledge_graph
    if _knowledge_graph is None:
        _knowledge_graph = KnowledgeGraph()
    return _knowledge_graph
