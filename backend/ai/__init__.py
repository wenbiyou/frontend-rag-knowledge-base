"""
AI 模块
包含 LLM 客户端、AI 导师、推荐引擎、知识图谱等 AI 功能
"""
from .deepseek_client import get_llm_client, get_embedding_client
from .ai_mentor import get_ai_mentor
from .recommendation import get_recommendation_engine
from .knowledge_graph import get_knowledge_graph

__all__ = [
    'get_llm_client',
    'get_embedding_client',
    'get_ai_mentor',
    'get_recommendation_engine',
    'get_knowledge_graph',
]
