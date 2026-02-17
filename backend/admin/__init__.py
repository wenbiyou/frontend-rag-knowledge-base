"""
管理模块
包含用户认证、API Key 管理、对话历史、文档管理、统计分析等管理功能
"""
from .auth import get_user_manager, create_token, get_current_user
from .api_keys import get_api_key_manager
from .chat_history import get_history_manager
from .document_manager import get_document_manager
from .analytics import get_analytics_manager
from .feedback import get_feedback_manager
from .github_db import get_all_repos, get_repo, add_repo, update_repo, delete_repo
from .code_analyzer import get_code_analyzer

__all__ = [
    'get_user_manager',
    'create_token',
    'get_current_user',
    'get_api_key_manager',
    'get_history_manager',
    'get_document_manager',
    'get_analytics_manager',
    'get_feedback_manager',
    'get_all_repos',
    'get_repo',
    'add_repo',
    'update_repo',
    'delete_repo',
    'get_code_analyzer',
]
