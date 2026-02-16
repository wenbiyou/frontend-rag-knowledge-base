"""
RAG 优化模块
实现重排序、多路召回、查询意图识别
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class QueryIntent(Enum):
    """查询意图类型"""
    CODE = "code"                    # 代码问题
    CONCEPT = "concept"              # 概念解释
    BEST_PRACTICE = "best_practice"  # 最佳实践
    ERROR_DEBUG = "error_debug"      # 错误调试
    COMPARISON = "comparison"        # 对比分析
    GENERAL = "general"              # 一般问题


@dataclass
class RerankResult:
    """重排序结果"""
    doc: str
    metadata: Dict
    original_score: float
    rerank_score: float
    intent_match: float


class QueryIntentClassifier:
    """查询意图分类器"""

    CODE_PATTERNS = [
        r'如何实现', r'怎么写', r'代码示例', r'代码怎么',
        r'函数', r'方法', r'组件', r'API',
        r'import', r'export', r'const', r'function',
        r'语法', r'报错', r'错误', r'异常',
        r'性能优化', r'重构', r'封装'
    ]

    CONCEPT_PATTERNS = [
        r'是什么', r'什么是', r'概念', r'原理',
        r'区别', r'对比', r'比较', r'异同',
        r'为什么', r'作用', r'用途', r'意义'
    ]

    BEST_PRACTICE_PATTERNS = [
        r'最佳实践', r'推荐', r'建议', r'规范',
        r'应该', r'最好', r'正确', r'合理',
        r'设计模式', r'架构', r'模式'
    ]

    ERROR_DEBUG_PATTERNS = [
        r'报错', r'错误', r'异常', r'bug',
        r'不工作', r'失败', r'崩溃', r'问题',
        r'为什么不行', r'怎么解决', r'修复'
    ]

    COMPARISON_PATTERNS = [
        r'区别', r'对比', r'比较', r'哪个好',
        r'vs', r'VS', r'还是', r'或者',
        r'优缺点', r'优劣'
    ]

    @classmethod
    def classify(cls, query: str) -> QueryIntent:
        """分类查询意图"""
        query_lower = query.lower()

        comparison_score = sum(1 for p in cls.COMPARISON_PATTERNS if re.search(p, query))
        if comparison_score >= 1:
            return QueryIntent.COMPARISON

        error_score = sum(1 for p in cls.ERROR_DEBUG_PATTERNS if re.search(p, query))
        if error_score >= 1:
            return QueryIntent.ERROR_DEBUG

        code_score = sum(1 for p in cls.CODE_PATTERNS if re.search(p, query))
        concept_score = sum(1 for p in cls.CONCEPT_PATTERNS if re.search(p, query))
        practice_score = sum(1 for p in cls.BEST_PRACTICE_PATTERNS if re.search(p, query))

        scores = {
            QueryIntent.CODE: code_score,
            QueryIntent.CONCEPT: concept_score,
            QueryIntent.BEST_PRACTICE: practice_score
        }

        max_intent = max(scores, key=scores.get)
        if scores[max_intent] > 0:
            return max_intent

        return QueryIntent.GENERAL

    @classmethod
    def get_intent_keywords(cls, intent: QueryIntent) -> List[str]:
        """获取意图相关的关键词"""
        patterns_map = {
            QueryIntent.CODE: cls.CODE_PATTERNS,
            QueryIntent.CONCEPT: cls.CONCEPT_PATTERNS,
            QueryIntent.BEST_PRACTICE: cls.BEST_PRACTICE_PATTERNS,
            QueryIntent.ERROR_DEBUG: cls.ERROR_DEBUG_PATTERNS,
            QueryIntent.COMPARISON: cls.COMPARISON_PATTERNS,
        }
        return patterns_map.get(intent, [])


class Reranker:
    """重排序器"""

    @staticmethod
    def extract_keywords(text: str) -> set:
        """提取关键词"""
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)
        chinese = re.findall(r'[\u4e00-\u9fff]+', text)
        return set(words + chinese)

    @staticmethod
    def calculate_intent_relevance(doc: str, metadata: Dict, intent: QueryIntent) -> float:
        """计算文档与意图的相关性"""
        keywords = QueryIntentClassifier.get_intent_keywords(intent)
        doc_lower = doc.lower()

        matches = sum(1 for kw in keywords if kw.lower() in doc_lower)
        return min(matches / max(len(keywords), 1), 1.0)

    @classmethod
    def rerank(
        cls,
        docs: List[str],
        metas: List[Dict],
        scores: List[float],
        query: str,
        intent: QueryIntent = None
    ) -> List[RerankResult]:
        """重排序文档"""
        if not intent:
            intent = QueryIntentClassifier.classify(query)

        query_keywords = cls.extract_keywords(query)
        results = []

        for i, (doc, meta, score) in enumerate(zip(docs, metas, scores)):
            doc_keywords = cls.extract_keywords(doc)

            keyword_overlap = len(query_keywords & doc_keywords) / max(len(query_keywords), 1)

            intent_match = cls.calculate_intent_relevance(doc, meta, intent)

            position_weight = 1.0 / (i + 1)

            rerank_score = (
                score * 0.4 +
                keyword_overlap * 0.3 +
                intent_match * 0.2 +
                position_weight * 0.1
            )

            results.append(RerankResult(
                doc=doc,
                metadata=meta,
                original_score=score,
                rerank_score=rerank_score,
                intent_match=intent_match
            ))

        results.sort(key=lambda x: x.rerank_score, reverse=True)
        return results


class MultiRetriever:
    """多路召回器"""

    @staticmethod
    def keyword_search(query: str, documents: List[Dict], top_k: int = 5) -> List[Tuple[Dict, float]]:
        """关键词检索"""
        query_terms = set(re.findall(r'\w+', query.lower()))
        results = []

        for doc in documents:
            content = doc.get('content', '').lower()
            title = doc.get('title', '').lower()

            content_terms = set(re.findall(r'\w+', content))
            title_terms = set(re.findall(r'\w+', title))

            content_overlap = len(query_terms & content_terms)
            title_overlap = len(query_terms & title_terms) * 2

            score = (content_overlap + title_overlap) / max(len(query_terms), 1)
            results.append((doc, score))

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    @staticmethod
    def fuse_results(
        vector_results: List[Tuple[Dict, float]],
        keyword_results: List[Tuple[Dict, float]],
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4
    ) -> List[Tuple[Dict, float]]:
        """融合多路召回结果"""
        doc_scores = {}

        for doc, score in vector_results:
            doc_id = doc.get('id') or doc.get('source', '') + doc.get('title', '')
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score * vector_weight

        for doc, score in keyword_results:
            doc_id = doc.get('id') or doc.get('source', '') + doc.get('title', '')
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + score * keyword_weight

        all_docs = {doc.get('id') or doc.get('source', '') + doc.get('title', ''): doc
                    for doc, _ in vector_results + keyword_results}

        fused = [(all_docs[doc_id], score) for doc_id, score in doc_scores.items()]
        fused.sort(key=lambda x: x[1], reverse=True)

        return fused


class RAGOptimizer:
    """RAG 优化器"""

    def __init__(self):
        self.reranker = Reranker()
        self.classifier = QueryIntentClassifier()

    def optimize_query(self, query: str) -> Dict:
        """优化查询"""
        intent = self.classifier.classify(query)
        keywords = self.classifier.get_intent_keywords(intent)

        return {
            "original_query": query,
            "intent": intent.value,
            "intent_keywords": keywords,
            "suggested_sources": self._get_suggested_sources(intent)
        }

    def _get_suggested_sources(self, intent: QueryIntent) -> List[str]:
        """根据意图推荐来源"""
        source_map = {
            QueryIntent.CODE: ["github", "document"],
            QueryIntent.CONCEPT: ["official", "document"],
            QueryIntent.BEST_PRACTICE: ["official", "github"],
            QueryIntent.ERROR_DEBUG: ["github", "document"],
            QueryIntent.COMPARISON: ["official", "document"],
            QueryIntent.GENERAL: ["official", "document", "github"]
        }
        return source_map.get(intent, ["official", "document", "github"])

    def enhance_retrieval(
        self,
        query: str,
        docs: List[str],
        metas: List[Dict],
        scores: List[float]
    ) -> Dict:
        """增强检索结果"""
        intent = self.classifier.classify(query)
        reranked = self.reranker.rerank(docs, metas, scores, query, intent)

        return {
            "intent": intent.value,
            "results": [
                {
                    "content": r.doc[:500] + "..." if len(r.doc) > 500 else r.doc,
                    "metadata": r.metadata,
                    "original_score": round(r.original_score, 4),
                    "rerank_score": round(r.rerank_score, 4),
                    "intent_match": round(r.intent_match, 4)
                }
                for r in reranked
            ]
        }


_rag_optimizer = None


def get_rag_optimizer() -> RAGOptimizer:
    """获取 RAG 优化器单例"""
    global _rag_optimizer
    if _rag_optimizer is None:
        _rag_optimizer = RAGOptimizer()
    return _rag_optimizer
