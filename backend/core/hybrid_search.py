"""
混合检索模块
结合向量检索和关键词检索，提高召回率
"""
import math
import re
from typing import List, Dict, Tuple
from collections import Counter

from config import (
    ENABLE_HYBRID_SEARCH,
    KEYWORD_WEIGHT,
    VECTOR_WEIGHT,
    ENABLE_QUERY_EXPANSION,
    QUERY_EXPANSION_TERMS,
    INITIAL_TOP_K,
)


class QueryExpander:
    """查询扩展器"""

    @staticmethod
    def expand(query: str) -> List[str]:
        """
        扩展查询词，生成多个相关查询

        Args:
            query: 原始查询

        Returns:
            扩展后的查询列表
        """
        if not ENABLE_QUERY_EXPANSION:
            return [query]

        queries = [query]
        query_lower = query.lower()

        for term, expansions in QUERY_EXPANSION_TERMS.items():
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, query_lower):
                for exp in expansions:
                    new_query = re.sub(
                        pattern,
                        exp,
                        query,
                        flags=re.IGNORECASE
                    )
                    if new_query not in queries:
                        queries.append(new_query)

        return queries[:5]

    @staticmethod
    def get_primary_expansion(query: str) -> str:
        """
        获取主要扩展查询（用于向量检索）

        Args:
            query: 原始查询

        Returns:
            扩展后的主查询
        """
        query_lower = query.lower()

        for term, expansions in QUERY_EXPANSION_TERMS.items():
            pattern = r'\b' + re.escape(term) + r'\b'
            if re.search(pattern, query_lower):
                return re.sub(
                    pattern,
                    expansions[0],
                    query,
                    flags=re.IGNORECASE
                )

        return query


class BM25Scorer:
    """BM25 关键词检索评分器"""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.doc_freqs: Dict[str, int] = {}
        self.doc_lens: List[int] = []
        self.avgdl: float = 0
        self.n_docs: int = 0

    def fit(self, documents: List[str]):
        """
        计算 IDF 和文档长度统计

        Args:
            documents: 文档列表
        """
        self.n_docs = len(documents)
        self.doc_lens = []

        for doc in documents:
            tokens = self._tokenize(doc)
            self.doc_lens.append(len(tokens))

            seen = set()
            for token in tokens:
                if token not in seen:
                    self.doc_freqs[token] = self.doc_freqs.get(token, 0) + 1
                    seen.add(token)

        self.avgdl = sum(self.doc_lens) / self.n_docs if self.n_docs > 0 else 0

    def _tokenize(self, text: str) -> List[str]:
        """分词"""
        text = text.lower()
        tokens = re.findall(r'\w+', text)
        return tokens

    def score(self, query: str, documents: List[str]) -> List[float]:
        """
        计算 BM25 分数

        Args:
            query: 查询
            documents: 文档列表

        Returns:
            每个文档的 BM25 分数
        """
        query_tokens = self._tokenize(query)
        scores = []

        for i, doc in enumerate(documents):
            doc_tokens = self._tokenize(doc)
            doc_len = len(doc_tokens)
            tf = Counter(doc_tokens)

            score = 0.0
            for token in query_tokens:
                if token not in self.doc_freqs:
                    continue

                idf = math.log(
                    (self.n_docs - self.doc_freqs[token] + 0.5) /
                    (self.doc_freqs[token] + 0.5) + 1
                )

                term_freq = tf.get(token, 0)
                numerator = term_freq * (self.k1 + 1)
                denominator = term_freq + self.k1 * (
                    1 - self.b + self.b * doc_len / self.avgdl
                )
                score += idf * numerator / denominator

            scores.append(score)

        return scores


class HybridSearcher:
    """混合检索器"""

    def __init__(self):
        self.bm25 = BM25Scorer()
        self.query_expander = QueryExpander()

    def reciprocal_rank_fusion(
        self,
        results_list: List[List[Tuple[str, Dict, float]]],
        k: int = 60
    ) -> List[Tuple[str, Dict, float]]:
        """
        倒数排名融合（RRF）算法

        Args:
            results_list: 多个检索结果列表，每个元素是 (doc, meta, score)
            k: RRF 参数

        Returns:
            融合后的结果列表
        """
        rrf_scores: Dict[str, float] = {}
        doc_meta: Dict[str, Dict] = {}
        doc_content: Dict[str, str] = {}

        for results in results_list:
            for rank, (doc, meta, score) in enumerate(results):
                doc_id = meta.get('id', str(hash(doc)))

                if doc_id not in rrf_scores:
                    rrf_scores[doc_id] = 0
                    doc_meta[doc_id] = meta
                    doc_content[doc_id] = doc

                rrf_scores[doc_id] += 1 / (k + rank + 1)

        sorted_docs = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )

        return [
            (doc_content[doc_id], doc_meta[doc_id], score)
            for doc_id, score in sorted_docs
        ]

    def search(
        self,
        query: str,
        vector_results: List[Tuple[str, Dict, float]],
        documents: List[str],
        metadatas: List[Dict]
    ) -> List[Tuple[str, Dict, float]]:
        """
        执行混合检索

        Args:
            query: 查询
            vector_results: 向量检索结果 [(doc, meta, similarity)]
            documents: 所有文档（用于 BM25）
            metadatas: 所有文档元数据

        Returns:
            融合后的结果列表
        """
        if not ENABLE_HYBRID_SEARCH:
            return vector_results

        self.bm25.fit(documents)
        bm25_scores = self.bm25.score(query, documents)

        bm25_results = [
            (doc, meta, score)
            for doc, meta, score in zip(documents, metadatas, bm25_scores)
            if score > 0
        ]
        bm25_results.sort(key=lambda x: x[2], reverse=True)
        bm25_results = bm25_results[:INITIAL_TOP_K]

        vector_results_normalized = self._normalize_scores(vector_results)
        bm25_results_normalized = self._normalize_scores(bm25_results)

        for i, (doc, meta, score) in enumerate(vector_results_normalized):
            bm25_results_normalized.append(
                (doc, meta, score * VECTOR_WEIGHT)
            )

        for i, (doc, meta, score) in enumerate(bm25_results_normalized):
            if any(r[1].get('id') == meta.get('id') for r in vector_results_normalized):
                for j, (v_doc, v_meta, v_score) in enumerate(vector_results_normalized):
                    if v_meta.get('id') == meta.get('id'):
                        bm25_results_normalized[j] = (
                            v_doc, v_meta,
                            v_score * VECTOR_WEIGHT + score * KEYWORD_WEIGHT
                        )

        fused = self.reciprocal_rank_fusion([
            vector_results_normalized,
            bm25_results_normalized
        ])

        return fused

    def _normalize_scores(
        self,
        results: List[Tuple[str, Dict, float]]
    ) -> List[Tuple[str, Dict, float]]:
        """归一化分数到 0-1 范围"""
        if not results:
            return results

        scores = [r[2] for r in results]
        min_score = min(scores)
        max_score = max(scores)

        if max_score == min_score:
            return [(doc, meta, 1.0) for doc, meta, _ in results]

        return [
            (doc, meta, (score - min_score) / (max_score - min_score))
            for doc, meta, score in results
        ]


_hybrid_searcher = None


def get_hybrid_searcher() -> HybridSearcher:
    """获取混合检索器单例"""
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher()
    return _hybrid_searcher
