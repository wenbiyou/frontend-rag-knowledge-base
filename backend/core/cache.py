"""
响应缓存模块
缓存热门问题的回答，减少 LLM API 调用
"""
import hashlib
import time
from typing import Dict, Optional, Any
from threading import Lock
from config import ENABLE_CACHE, CACHE_TTL


class ResponseCache:
    """
    响应缓存管理器
    使用内存缓存，支持 TTL 过期
    """
    
    _instance: Optional['ResponseCache'] = None
    _lock = Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_lock = Lock()
        self._hits = 0
        self._misses = 0
    
    def _generate_key(self, query: str, source_filter: str = None) -> str:
        """生成缓存键"""
        content = f"{query}:{source_filter or ''}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, query: str, source_filter: str = None) -> Optional[Dict]:
        """获取缓存的响应"""
        if not ENABLE_CACHE:
            return None
        
        key = self._generate_key(query, source_filter)
        
        with self._cache_lock:
            if key in self._cache:
                entry = self._cache[key]
                if time.time() - entry['timestamp'] < CACHE_TTL:
                    self._hits += 1
                    return entry['data']
                else:
                    del self._cache[key]
        
        self._misses += 1
        return None
    
    def set(self, query: str, source_filter: str, data: Dict) -> None:
        """缓存响应"""
        if not ENABLE_CACHE:
            return
        
        key = self._generate_key(query, source_filter)
        
        with self._cache_lock:
            self._cache[key] = {
                'data': data,
                'timestamp': time.time()
            }
            
            if len(self._cache) > 1000:
                self._evict_expired()
    
    def _evict_expired(self) -> None:
        """清理过期缓存"""
        current_time = time.time()
        expired_keys = [
            k for k, v in self._cache.items()
            if current_time - v['timestamp'] >= CACHE_TTL
        ]
        for key in expired_keys:
            del self._cache[key]
    
    def clear(self) -> None:
        """清空缓存"""
        with self._cache_lock:
            self._cache.clear()
    
    def get_stats(self) -> Dict:
        """获取缓存统计"""
        total = self._hits + self._misses
        hit_rate = self._hits / total * 100 if total > 0 else 0
        return {
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': f"{hit_rate:.1f}%",
            'cache_size': len(self._cache),
            'enabled': ENABLE_CACHE,
            'ttl': CACHE_TTL
        }


_cache: Optional[ResponseCache] = None


def get_cache() -> ResponseCache:
    """获取缓存单例"""
    global _cache
    if _cache is None:
        _cache = ResponseCache()
    return _cache
