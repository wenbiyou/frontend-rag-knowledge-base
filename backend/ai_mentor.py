"""
AI 导师模块
提供技能评估、学习计划、技术文章推送等功能
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from config import BASE_DIR

MENTOR_DB_PATH = BASE_DIR / "mentor.db"


class AIMentor:
    """AI 导师"""

    def __init__(self):
        self.db_path = MENTOR_DB_PATH
        self._init_db()
        self._init_default_content()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skill_assessments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    skill_name TEXT NOT NULL,
                    score INTEGER NOT NULL,
                    max_score INTEGER DEFAULT 100,
                    answers TEXT,
                    assessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS learning_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    skills TEXT NOT NULL,
                    timeline_weeks INTEGER DEFAULT 4,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS plan_progress (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    plan_id INTEGER NOT NULL,
                    skill_name TEXT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    progress INTEGER DEFAULT 0,
                    notes TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (plan_id) REFERENCES learning_plans(id)
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS article_recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    title TEXT NOT NULL,
                    url TEXT,
                    summary TEXT,
                    category TEXT,
                    difficulty INTEGER DEFAULT 1,
                    is_read BOOLEAN DEFAULT FALSE,
                    recommended_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS growth_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    record_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_assessments_user
                ON skill_assessments(user_id, skill_name)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_plans_user
                ON learning_plans(user_id, status)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_articles_user
                ON article_recommendations(user_id, is_read)
            """)

            conn.commit()

    def _init_default_content(self):
        """初始化默认内容"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM article_recommendations")
            if cursor.fetchone()[0] > 0:
                return

            articles = [
                ("Vue3 Composition API 完全指南", "https://vuejs.org/guide/extras/composition-api-faq.html", "深入理解 Vue3 组合式 API 的核心概念和最佳实践", "Vue", 2),
                ("React Hooks 最佳实践", "https://react.dev/reference/react", "掌握 React Hooks 的正确使用方式", "React", 2),
                ("TypeScript 高级类型技巧", "https://www.typescriptlang.org/docs/handbook/2/types-from-types.html", "学习 TypeScript 高级类型系统", "TypeScript", 3),
                ("前端性能优化实战", None, "从首屏加载到运行时性能的全面优化指南", "性能优化", 3),
                ("CSS Grid 布局完全指南", None, "掌握现代 CSS 布局技术", "CSS", 2),
                ("JavaScript 异步编程详解", None, "深入理解 Promise、async/await 和事件循环", "JavaScript", 2),
                ("前端工程化最佳实践", None, "Webpack、Vite 配置与优化", "工程化", 3),
                ("微前端架构设计", None, "企业级微前端解决方案", "架构", 4),
            ]

            for title, url, summary, category, difficulty in articles:
                cursor.execute(
                    """
                    INSERT INTO article_recommendations (title, url, summary, category, difficulty)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (title, url, summary, category, difficulty)
                )

            conn.commit()

    def get_assessment_questions(self, skill: str) -> List[Dict]:
        """获取技能评估问题"""
        questions_map = {
            "JavaScript": [
                {
                    "question": "以下哪个不是 JavaScript 的基本数据类型？",
                    "options": ["string", "number", "array", "boolean"],
                    "correct": 2,
                    "explanation": "Array 是对象类型，不是基本数据类型"
                },
                {
                    "question": "Promise 的三种状态是？",
                    "options": ["start, running, end", "pending, fulfilled, rejected", "wait, success, fail", "init, done, error"],
                    "correct": 1,
                    "explanation": "Promise 有 pending、fulfilled、rejected 三种状态"
                },
                {
                    "question": "以下哪个方法会改变原数组？",
                    "options": ["map", "filter", "splice", "concat"],
                    "correct": 2,
                    "explanation": "splice 会直接修改原数组"
                },
            ],
            "Vue": [
                {
                    "question": "Vue3 中 ref 和 reactive 的主要区别是？",
                    "options": ["没有区别", "ref 用于基本类型，reactive 用于对象", "ref 需要解包，reactive 不需要", "B 和 C 都对"],
                    "correct": 3,
                    "explanation": "ref 适合基本类型，需要 .value 访问；reactive 适合对象类型"
                },
                {
                    "question": "Vue 的生命周期中，哪个钩子最适合发送 API 请求？",
                    "options": ["beforeCreate", "created", "beforeMount", "mounted"],
                    "correct": 3,
                    "explanation": "mounted 钩子时 DOM 已挂载，适合进行 DOM 操作和 API 请求"
                },
            ],
            "React": [
                {
                    "question": "React Hooks 中，useEffect 的依赖数组为空数组时，效果等同于？",
                    "options": ["componentDidMount", "componentDidUpdate", "componentWillUnmount", "没有效果"],
                    "correct": 0,
                    "explanation": "空依赖数组使 useEffect 只在挂载时执行一次"
                },
                {
                    "question": "以下哪个 Hook 用于性能优化？",
                    "options": ["useState", "useEffect", "useMemo", "useContext"],
                    "correct": 2,
                    "explanation": "useMemo 可以缓存计算结果，避免不必要的重新计算"
                },
            ],
            "TypeScript": [
                {
                    "question": "interface 和 type 的主要区别是？",
                    "options": ["没有区别", "interface 可以被扩展，type 可以有联合类型", "type 更快", "interface 只能用于对象"],
                    "correct": 1,
                    "explanation": "interface 支持声明合并和扩展，type 支持更复杂的类型操作"
                },
                {
                    "question": "以下哪个是正确的泛型函数定义？",
                    "options": ["function fn[T](arg: T)", "function fn(arg: T)", "function fn<T>(arg: T)", "function fn<T>(arg: any)"],
                    "correct": 2,
                    "explanation": "TypeScript 泛型使用 <T> 语法定义"
                },
            ],
            "CSS": [
                {
                    "question": "Flexbox 中，justify-content 控制的是？",
                    "options": ["垂直对齐", "水平对齐", "换行方式", "元素顺序"],
                    "correct": 1,
                    "explanation": "justify-content 控制主轴方向的对齐方式"
                },
                {
                    "question": "以下哪个单位是相对于根元素字体大小？",
                    "options": ["em", "rem", "px", "vh"],
                    "correct": 1,
                    "explanation": "rem 是相对于根元素 html 的字体大小"
                },
            ],
        }

        return questions_map.get(skill, [])

    def submit_assessment(
        self,
        user_id: int,
        skill: str,
        answers: List[int]
    ) -> Dict:
        """提交技能评估"""
        questions = self.get_assessment_questions(skill)

        if not questions:
            return {"error": "未找到该技能的评估问题"}

        correct_count = 0
        answer_details = []

        for i, (question, answer) in enumerate(zip(questions, answers)):
            is_correct = answer == question["correct"]
            if is_correct:
                correct_count += 1

            answer_details.append({
                "question": question["question"],
                "user_answer": question["options"][answer],
                "correct_answer": question["options"][question["correct"]],
                "is_correct": is_correct,
                "explanation": question["explanation"]
            })

        score = int((correct_count / len(questions)) * 100)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO skill_assessments (user_id, skill_name, score, answers)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, skill, score, json.dumps(answer_details, ensure_ascii=False))
            )

            conn.commit()

        level = self._get_skill_level(score)

        return {
            "skill": skill,
            "score": score,
            "correct_count": correct_count,
            "total_questions": len(questions),
            "level": level,
            "details": answer_details
        }

    def _get_skill_level(self, score: int) -> str:
        """获取技能等级"""
        if score >= 90:
            return "专家"
        elif score >= 70:
            return "熟练"
        elif score >= 50:
            return "入门"
        else:
            return "初学"

    def get_user_skills(self, user_id: int) -> List[Dict]:
        """获取用户技能评估历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT skill_name, score, max_score, assessed_at
                FROM skill_assessments
                WHERE user_id = ?
                ORDER BY assessed_at DESC
                """,
                (user_id,)
            )

            return [dict(row) for row in cursor.fetchall()]

    def create_learning_plan(
        self,
        user_id: int,
        name: str,
        skills: List[str],
        timeline_weeks: int = 4,
        description: str = None
    ) -> Dict:
        """创建学习计划"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO learning_plans (user_id, name, description, skills, timeline_weeks)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, name, description, json.dumps(skills, ensure_ascii=False), timeline_weeks)
            )

            plan_id = cursor.lastrowid

            for skill in skills:
                cursor.execute(
                    """
                    INSERT INTO plan_progress (plan_id, skill_name)
                    VALUES (?, ?)
                    """,
                    (plan_id, skill)
                )

            conn.commit()

        return {
            "id": plan_id,
            "name": name,
            "skills": skills,
            "timeline_weeks": timeline_weeks,
            "status": "active"
        }

    def get_user_plans(self, user_id: int) -> List[Dict]:
        """获取用户学习计划"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, name, description, skills, timeline_weeks, status, created_at
                FROM learning_plans
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )

            plans = []
            for row in cursor.fetchall():
                plan = dict(row)
                plan["skills"] = json.loads(plan["skills"])

                cursor.execute(
                    """
                    SELECT skill_name, status, progress, notes
                    FROM plan_progress
                    WHERE plan_id = ?
                    """,
                    (plan["id"],)
                )
                plan["progress"] = [dict(r) for r in cursor.fetchall()]

                plans.append(plan)

            return plans

    def update_plan_progress(
        self,
        plan_id: int,
        skill_name: str,
        progress: int,
        notes: str = None
    ) -> bool:
        """更新学习进度"""
        status = "completed" if progress >= 100 else "in_progress" if progress > 0 else "pending"

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                UPDATE plan_progress
                SET progress = ?, status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE plan_id = ? AND skill_name = ?
                """,
                (progress, status, notes, plan_id, skill_name)
            )

            conn.commit()
            return cursor.rowcount > 0

    def get_article_recommendations(
        self,
        user_id: int = None,
        category: str = None,
        unread_only: bool = False,
        limit: int = 10
    ) -> List[Dict]:
        """获取文章推荐"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            query = "SELECT * FROM article_recommendations WHERE 1=1"
            params = []

            if user_id is not None:
                query += " AND (user_id = ? OR user_id IS NULL)"
                params.append(user_id)

            if category:
                query += " AND category = ?"
                params.append(category)

            if unread_only:
                query += " AND is_read = FALSE"

            query += " ORDER BY recommended_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)

            return [dict(row) for row in cursor.fetchall()]

    def mark_article_read(self, article_id: int) -> bool:
        """标记文章已读"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE article_recommendations SET is_read = TRUE WHERE id = ?",
                (article_id,)
            )

            conn.commit()
            return cursor.rowcount > 0

    def add_growth_record(
        self,
        user_id: int,
        record_type: str,
        content: str
    ) -> Dict:
        """添加成长记录"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO growth_records (user_id, record_type, content)
                VALUES (?, ?, ?)
                """,
                (user_id, record_type, content)
            )

            conn.commit()

            return {
                "id": cursor.lastrowid,
                "record_type": record_type,
                "content": content,
                "created_at": datetime.now().isoformat()
            }

    def get_growth_records(
        self,
        user_id: int,
        record_type: str = None,
        limit: int = 20
    ) -> List[Dict]:
        """获取成长记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if record_type:
                cursor.execute(
                    """
                    SELECT id, record_type, content, created_at
                    FROM growth_records
                    WHERE user_id = ? AND record_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (user_id, record_type, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, record_type, content, created_at
                    FROM growth_records
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (user_id, limit)
                )

            return [dict(row) for row in cursor.fetchall()]

    def get_growth_summary(self, user_id: int) -> Dict:
        """获取成长总结"""
        skills = self.get_user_skills(user_id)
        plans = self.get_user_plans(user_id)
        records = self.get_growth_records(user_id, limit=50)

        skill_levels = {}
        for skill in skills:
            name = skill["skill_name"]
            if name not in skill_levels or skill["score"] > skill_levels[name]["score"]:
                skill_levels[name] = skill

        active_plans = [p for p in plans if p["status"] == "active"]
        completed_plans = [p for p in plans if p["status"] == "completed"]

        record_types = {}
        for record in records:
            rtype = record["record_type"]
            record_types[rtype] = record_types.get(rtype, 0) + 1

        return {
            "total_skills_assessed": len(skill_levels),
            "skill_levels": skill_levels,
            "active_plans": len(active_plans),
            "completed_plans": len(completed_plans),
            "total_records": len(records),
            "record_types": record_types
        }


_ai_mentor = None


def get_ai_mentor() -> AIMentor:
    """获取 AI 导师单例"""
    global _ai_mentor
    if _ai_mentor is None:
        _ai_mentor = AIMentor()
    return _ai_mentor
