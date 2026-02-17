"""
主动推荐模块
基于用户行为分析，提供个性化推荐和智能报告
"""
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import Counter
from config import AI_DB_PATH


class RecommendationEngine:
    """推荐引擎"""

    def __init__(self):
        self.db_path = AI_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_interests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    topic TEXT NOT NULL,
                    score REAL DEFAULT 1.0,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    report_date DATE NOT NULL,
                    report_type TEXT DEFAULT 'daily',
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS recommendations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    topic TEXT NOT NULL,
                    reason TEXT,
                    score REAL DEFAULT 0.5,
                    is_shown BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_interests_user
                ON user_interests(user_id, topic)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_reports_user_date
                ON daily_reports(user_id, report_date)
            """)

            conn.commit()

    def analyze_interests(self, user_id: int, questions: List[str]) -> Dict:
        """分析用户兴趣"""
        topics = self._extract_topics(questions)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            for topic, count in topics.items():
                cursor.execute(
                    """
                    INSERT INTO user_interests (user_id, topic, score, last_updated)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, topic) DO UPDATE SET
                        score = score + ?,
                        last_updated = CURRENT_TIMESTAMP
                    """,
                    (user_id, topic, count * 0.1, count * 0.1)
                )

            conn.commit()

        return {
            "user_id": user_id,
            "topics_analyzed": len(topics),
            "top_interests": topics.most_common(5)
        }

    def _extract_topics(self, questions: List[str]) -> Counter:
        """从问题中提取主题"""
        topic_keywords = {
            'Vue': ['vue', 'vue3', 'vue2', 'vuex', 'pinia', 'vue-router', 'composition api'],
            'React': ['react', 'react hooks', 'redux', 'react-router', 'jsx', 'next.js'],
            'TypeScript': ['typescript', 'ts', '类型', 'interface', 'type'],
            'JavaScript': ['javascript', 'js', 'es6', 'es7', 'promise', 'async', 'await'],
            'CSS': ['css', 'scss', 'sass', 'less', 'flex', 'grid', '样式'],
            '性能优化': ['性能', '优化', '加载', '缓存', '懒加载', '性能优化'],
            '工程化': ['webpack', 'vite', 'rollup', '构建', '打包', '工程化'],
            '测试': ['测试', 'jest', 'vitest', '单元测试', 'e2e', '测试'],
            'Node.js': ['node', 'nodejs', 'express', 'koa', 'nest', '后端'],
            '移动端': ['移动端', '小程序', 'react native', 'flutter', 'hybrid'],
        }

        topics = Counter()

        for question in questions:
            question_lower = question.lower()
            for topic, keywords in topic_keywords.items():
                for keyword in keywords:
                    if keyword in question_lower:
                        topics[topic] += 1
                        break

        return topics

    def get_user_interests(self, user_id: int, limit: int = 10) -> List[Dict]:
        """获取用户兴趣列表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT topic, score, last_updated
                FROM user_interests
                WHERE user_id = ?
                ORDER BY score DESC
                LIMIT ?
                """,
                (user_id, limit)
            )

            return [dict(row) for row in cursor.fetchall()]

    def generate_recommendations(self, user_id: int, limit: int = 5) -> List[Dict]:
        """生成个性化推荐"""
        interests = self.get_user_interests(user_id, limit=10)

        if not interests:
            return self._get_popular_recommendations(limit)

        recommendations = []
        for interest in interests[:limit]:
            topic = interest['topic']
            score = interest['score']

            recommendations.append({
                'topic': topic,
                'reason': f'基于您对 {topic} 的关注',
                'score': score,
                'suggested_questions': self._get_suggested_questions(topic)
            })

        return recommendations

    def _get_popular_recommendations(self, limit: int = 5) -> List[Dict]:
        """获取热门推荐"""
        popular_topics = [
            {'topic': 'Vue3', 'reason': '热门技术', 'score': 0.9},
            {'topic': 'TypeScript', 'reason': '热门技术', 'score': 0.85},
            {'topic': 'React Hooks', 'reason': '热门技术', 'score': 0.8},
            {'topic': '性能优化', 'reason': '热门技术', 'score': 0.75},
            {'topic': 'CSS Grid', 'reason': '热门技术', 'score': 0.7},
        ]

        for topic in popular_topics[:limit]:
            topic['suggested_questions'] = self._get_suggested_questions(topic['topic'])

        return popular_topics[:limit]

    def _get_suggested_questions(self, topic: str) -> List[str]:
        """获取推荐问题"""
        suggestions = {
            'Vue': [
                'Vue3 的 Composition API 有什么优势？',
                'Vue 的响应式原理是什么？',
                'Pinia 和 Vuex 有什么区别？'
            ],
            'React': [
                'React Hooks 的使用场景有哪些？',
                'React 的虚拟 DOM 是如何工作的？',
                '如何优化 React 应用性能？'
            ],
            'TypeScript': [
                'TypeScript 的泛型如何使用？',
                'interface 和 type 有什么区别？',
                '如何为 React 组件添加类型？'
            ],
            'JavaScript': [
                'Promise 的实现原理是什么？',
                'ES6 有哪些新特性？',
                '如何理解 JavaScript 的闭包？'
            ],
            'CSS': [
                'Flex 布局有哪些常用属性？',
                'CSS Grid 如何实现响应式布局？',
                '如何实现 CSS 动画？'
            ],
            '性能优化': [
                '前端性能优化的常用方法有哪些？',
                '如何减少首屏加载时间？',
                '图片懒加载如何实现？'
            ],
        }

        return suggestions.get(topic, [
            f'{topic} 的核心概念是什么？',
            f'如何学习 {topic}？',
            f'{topic} 有哪些最佳实践？'
        ])

    def generate_daily_report(self, user_id: int) -> Dict:
        """生成日报"""
        today = datetime.now().strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id FROM daily_reports
                WHERE user_id = ? AND report_date = ? AND report_type = 'daily'
                """,
                (user_id, today)
            )

            if cursor.fetchone():
                return {"message": "今日日报已生成", "date": today}

        from analytics import get_analytics_manager
        analytics = get_analytics_manager()

        today_stats = analytics.get_daily_stats(today)

        report_content = {
            "date": today,
            "summary": {
                "total_questions": today_stats.get('total_questions', 0),
                "avg_response_time": today_stats.get('avg_response_time', 0),
                "satisfaction_rate": today_stats.get('satisfaction_rate', 0)
            },
            "top_topics": self.get_user_interests(user_id, limit=5),
            "recommendations": self.generate_recommendations(user_id, limit=3),
            "tips": self._get_daily_tips()
        }

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO daily_reports (user_id, report_date, report_type, content)
                VALUES (?, ?, 'daily', ?)
                """,
                (user_id, today, json.dumps(report_content, ensure_ascii=False))
            )

            conn.commit()

        return report_content

    def generate_weekly_report(self, user_id: int) -> Dict:
        """生成周报"""
        today = datetime.now()
        week_start = (today - timedelta(days=today.weekday())).strftime('%Y-%m-%d')

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id FROM daily_reports
                WHERE user_id = ? AND report_date = ? AND report_type = 'weekly'
                """,
                (user_id, week_start)
            )

            if cursor.fetchone():
                return {"message": "本周周报已生成", "week_start": week_start}

        from analytics import get_analytics_manager
        analytics = get_analytics_manager()

        weekly_stats = analytics.get_weekly_stats()

        report_content = {
            "week_start": week_start,
            "summary": weekly_stats,
            "interests_trend": self.get_user_interests(user_id, limit=10),
            "learning_suggestions": self._get_learning_suggestions(user_id),
            "next_week_plan": self._generate_next_week_plan(user_id)
        }

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT INTO daily_reports (user_id, report_date, report_type, content)
                VALUES (?, ?, 'weekly', ?)
                """,
                (user_id, week_start, json.dumps(report_content, ensure_ascii=False))
            )

            conn.commit()

        return report_content

    def _get_daily_tips(self) -> List[str]:
        """获取每日提示"""
        tips = [
            "使用 Composition API 可以更好地组织代码逻辑",
            "TypeScript 可以帮助你在编译时发现潜在错误",
            "合理使用 computed 和 watch 可以优化性能",
            "虚拟滚动可以大幅提升长列表性能",
            "CSS Grid 布局比 Flex 更适合二维布局",
            "使用 async/await 可以让异步代码更易读",
            "React.memo 可以避免不必要的组件重渲染",
            "使用 CSS 变量可以方便地实现主题切换",
        ]
        import random
        return random.sample(tips, min(3, len(tips)))

    def _get_learning_suggestions(self, user_id: int) -> List[str]:
        """获取学习建议"""
        interests = self.get_user_interests(user_id, limit=3)

        suggestions = []
        for interest in interests:
            topic = interest['topic']
            suggestions.append(f"建议深入学习 {topic} 的高级用法")

        if len(suggestions) < 3:
            suggestions.extend([
                "尝试学习一个新的前端框架",
                "关注前端性能优化实践",
                "学习前端工程化最佳实践"
            ])

        return suggestions[:3]

    def _generate_next_week_plan(self, user_id: int) -> List[str]:
        """生成下周计划"""
        interests = self.get_user_interests(user_id, limit=2)

        plans = []
        for interest in interests:
            topic = interest['topic']
            plans.append(f"完成 {topic} 进阶学习")

        plans.append("阅读 2 篇技术文章")

        return plans

    def get_report_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        """获取报告历史"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT id, report_date, report_type, created_at
                FROM daily_reports
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit)
            )

            return [dict(row) for row in cursor.fetchall()]


_recommendation_engine = None


def get_recommendation_engine() -> RecommendationEngine:
    """获取推荐引擎单例"""
    global _recommendation_engine
    if _recommendation_engine is None:
        _recommendation_engine = RecommendationEngine()
    return _recommendation_engine
