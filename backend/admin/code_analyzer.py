"""
代码理解增强模块
支持代码文件分析、结构解析、代码索引
"""
import os
import re
import json
import hashlib
import sqlite3
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from config import BASE_DIR

CODE_ANALYSIS_DB_PATH = BASE_DIR / "code_analysis.db"


@dataclass
class CodeFile:
    """代码文件信息"""
    id: str
    filename: str
    language: str
    content: str
    functions: List[Dict]
    classes: List[Dict]
    imports: List[str]
    exports: List[str]
    line_count: int
    created_at: str


@dataclass
class CodeSnippet:
    """代码片段"""
    id: str
    file_id: str
    type: str  # function, class, method, variable
    name: str
    content: str
    start_line: int
    end_line: int
    docstring: Optional[str]
    parameters: List[str]


class LanguageDetector:
    """语言检测器"""

    EXTENSIONS = {
        '.js': 'javascript',
        '.jsx': 'javascript',
        '.ts': 'typescript',
        '.tsx': 'typescript',
        '.vue': 'vue',
        '.py': 'python',
        '.java': 'java',
        '.go': 'go',
        '.rs': 'rust',
        '.c': 'c',
        '.cpp': 'cpp',
        '.h': 'c',
        '.hpp': 'cpp',
        '.css': 'css',
        '.scss': 'scss',
        '.less': 'less',
        '.html': 'html',
        '.json': 'json',
        '.md': 'markdown',
        '.yaml': 'yaml',
        '.yml': 'yaml',
        '.sh': 'shell',
        '.sql': 'sql',
    }

    @classmethod
    def detect(cls, filename: str) -> str:
        """检测文件语言"""
        ext = Path(filename).suffix.lower()
        return cls.EXTENSIONS.get(ext, 'unknown')


class CodeParser:
    """代码解析器"""

    @staticmethod
    def parse_javascript(content: str) -> Dict:
        """解析 JavaScript/TypeScript 代码"""
        functions = []
        classes = []
        imports = []
        exports = []

        func_pattern = r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)'
        for match in re.finditer(func_pattern, content):
            functions.append({
                'name': match.group(1),
                'params': [p.strip() for p in match.group(2).split(',') if p.strip()],
                'start': content[:match.start()].count('\n') + 1
            })

        arrow_pattern = r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)|[^=])\s*=>'
        for match in re.finditer(arrow_pattern, content):
            functions.append({
                'name': match.group(1),
                'params': [],
                'start': content[:match.start()].count('\n') + 1
            })

        class_pattern = r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?'
        for match in re.finditer(class_pattern, content):
            classes.append({
                'name': match.group(1),
                'extends': match.group(2),
                'start': content[:match.start()].count('\n') + 1
            })

        import_pattern = r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]'
        for match in re.finditer(import_pattern, content):
            imports.append(match.group(1))

        export_pattern = r'export\s+(?:default\s+)?(?:class|function|const|let|var)?\s*(\w+)'
        for match in re.finditer(export_pattern, content):
            exports.append(match.group(1))

        return {
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'exports': exports
        }

    @staticmethod
    def parse_python(content: str) -> Dict:
        """解析 Python 代码"""
        functions = []
        classes = []
        imports = []
        exports = []

        func_pattern = r'def\s+(\w+)\s*\(([^)]*)\):'
        for match in re.finditer(func_pattern, content):
            functions.append({
                'name': match.group(1),
                'params': [p.strip() for p in match.group(2).split(',') if p.strip()],
                'start': content[:match.start()].count('\n') + 1
            })

        class_pattern = r'class\s+(\w+)(?:\(([^)]*)\))?:'
        for match in re.finditer(class_pattern, content):
            classes.append({
                'name': match.group(1),
                'extends': match.group(2) if match.group(2) else None,
                'start': content[:match.start()].count('\n') + 1
            })

        import_pattern = r'(?:from\s+(\w+)\s+)?import\s+(.+)'
        for match in re.finditer(import_pattern, content):
            module = match.group(1) or ''
            names = match.group(2)
            imports.append(f"{module}.{names}" if module else names)

        return {
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'exports': exports
        }

    @staticmethod
    def parse_vue(content: str) -> Dict:
        """解析 Vue 组件"""
        functions = []
        classes = []
        imports = []
        exports = []

        script_match = re.search(r'<script[^>]*>(.*?)</script>', content, re.DOTALL)
        if script_match:
            script_content = script_match.group(1)
            js_result = CodeParser.parse_javascript(script_content)
            functions = js_result['functions']
            imports = js_result['imports']

        template_match = re.search(r'<template>(.*?)</template>', content, re.DOTALL)
        template_info = {}
        if template_match:
            template_content = template_match.group(1)
            components = re.findall(r'<(\w+(?:-\w+)*)', template_content)
            template_info['components_used'] = list(set(components))

        return {
            'functions': functions,
            'classes': classes,
            'imports': imports,
            'exports': exports,
            'template': template_info
        }

    @classmethod
    def parse(cls, content: str, language: str) -> Dict:
        """解析代码"""
        parsers = {
            'javascript': cls.parse_javascript,
            'typescript': cls.parse_javascript,
            'python': cls.parse_python,
            'vue': cls.parse_vue,
        }

        parser = parsers.get(language)
        if parser:
            return parser(content)

        return {
            'functions': [],
            'classes': [],
            'imports': [],
            'exports': []
        }


class CodeAnalyzer:
    """代码分析器"""

    def __init__(self):
        self.db_path = CODE_ANALYSIS_DB_PATH
        self._init_db()

    def _init_db(self):
        """初始化数据库"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    language TEXT NOT NULL,
                    content TEXT NOT NULL,
                    functions TEXT,
                    classes TEXT,
                    imports TEXT,
                    exports TEXT,
                    line_count INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS code_snippets (
                    id TEXT PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    start_line INTEGER,
                    end_line INTEGER,
                    docstring TEXT,
                    parameters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (file_id) REFERENCES code_files(id)
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snippets_file
                ON code_snippets(file_id)
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snippets_name
                ON code_snippets(name)
            """)

            conn.commit()

    def _generate_id(self, content: str) -> str:
        """生成唯一 ID"""
        return hashlib.md5(content.encode()).hexdigest()[:12]

    def analyze_file(self, filename: str, content: str) -> CodeFile:
        """分析代码文件"""
        language = LanguageDetector.detect(filename)
        parsed = CodeParser.parse(content, language)

        file_id = self._generate_id(f"{filename}:{content}")

        code_file = CodeFile(
            id=file_id,
            filename=filename,
            language=language,
            content=content,
            functions=parsed.get('functions', []),
            classes=parsed.get('classes', []),
            imports=parsed.get('imports', []),
            exports=parsed.get('exports', []),
            line_count=content.count('\n') + 1,
            created_at=datetime.now().isoformat()
        )

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                INSERT OR REPLACE INTO code_files
                (id, filename, language, content, functions, classes, imports, exports, line_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    code_file.id,
                    code_file.filename,
                    code_file.language,
                    code_file.content,
                    json.dumps(code_file.functions, ensure_ascii=False),
                    json.dumps(code_file.classes, ensure_ascii=False),
                    json.dumps(code_file.imports, ensure_ascii=False),
                    json.dumps(code_file.exports, ensure_ascii=False),
                    code_file.line_count,
                    code_file.created_at
                )
            )

            cursor.execute("DELETE FROM code_snippets WHERE file_id = ?", (file_id,))

            for func in parsed.get('functions', []):
                snippet_id = self._generate_id(f"{file_id}:func:{func['name']}")
                cursor.execute(
                    """
                    INSERT INTO code_snippets (id, file_id, type, name, content, start_line, parameters)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snippet_id,
                        file_id,
                        'function',
                        func['name'],
                        '',
                        func.get('start', 0),
                        json.dumps(func.get('params', []), ensure_ascii=False)
                    )
                )

            for cls in parsed.get('classes', []):
                snippet_id = self._generate_id(f"{file_id}:class:{cls['name']}")
                cursor.execute(
                    """
                    INSERT INTO code_snippets (id, file_id, type, name, content, start_line)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        snippet_id,
                        file_id,
                        'class',
                        cls['name'],
                        '',
                        cls.get('start', 0)
                    )
                )

            conn.commit()

        return code_file

    def get_file(self, file_id: str) -> Optional[Dict]:
        """获取文件信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM code_files WHERE id = ?", (file_id,))
            row = cursor.fetchone()

            if row:
                return dict(row)
            return None

    def list_files(self, language: str = None, limit: int = 50) -> List[Dict]:
        """列出代码文件"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            if language:
                cursor.execute(
                    """
                    SELECT id, filename, language, line_count, created_at
                    FROM code_files
                    WHERE language = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (language, limit)
                )
            else:
                cursor.execute(
                    """
                    SELECT id, filename, language, line_count, created_at
                    FROM code_files
                    ORDER BY created_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                )

            return [dict(row) for row in cursor.fetchall()]

    def search_snippets(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索代码片段"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            cursor.execute(
                """
                SELECT s.*, f.filename, f.language
                FROM code_snippets s
                JOIN code_files f ON s.file_id = f.id
                WHERE s.name LIKE ? OR f.filename LIKE ?
                ORDER BY s.created_at DESC
                LIMIT ?
                """,
                (f'%{query}%', f'%{query}%', limit)
            )

            return [dict(row) for row in cursor.fetchall()]

    def delete_file(self, file_id: str) -> bool:
        """删除代码文件"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("DELETE FROM code_snippets WHERE file_id = ?", (file_id,))
            cursor.execute("DELETE FROM code_files WHERE id = ?", (file_id,))

            conn.commit()
            return cursor.rowcount > 0

    def get_stats(self) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM code_files")
            total_files = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM code_snippets")
            total_snippets = cursor.fetchone()[0]

            cursor.execute(
                "SELECT language, COUNT(*) FROM code_files GROUP BY language"
            )
            by_language = {row[0]: row[1] for row in cursor.fetchall()}

            cursor.execute(
                "SELECT type, COUNT(*) FROM code_snippets GROUP BY type"
            )
            by_type = {row[0]: row[1] for row in cursor.fetchall()}

            return {
                'total_files': total_files,
                'total_snippets': total_snippets,
                'by_language': by_language,
                'by_type': by_type
            }


_code_analyzer = None


def get_code_analyzer() -> CodeAnalyzer:
    """获取代码分析器单例"""
    global _code_analyzer
    if _code_analyzer is None:
        _code_analyzer = CodeAnalyzer()
    return _code_analyzer
