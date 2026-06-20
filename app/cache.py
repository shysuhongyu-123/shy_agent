"""
缓存模块 — 使用内存缓存减少 LLM 调用和导师评分计算

用法：
    from app.cache import cache
    cache.set("key", value, ttl=300)  # 缓存5分钟
    value = cache.get("key")
"""

import time
import threading
import hashlib
import json
from typing import Any, Optional


class MemoryCache:
    """线程安全的内存缓存，支持 TTL"""

    def __init__(self):
        self._data = {}
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        """获取缓存值，如果过期或不存在返回 None"""
        with self._lock:
            entry = self._data.get(key)
            if entry is None:
                return None
            if entry["expires_at"] < time.time():
                del self._data[key]
                return None
            return entry["value"]

    def set(self, key: str, value: Any, ttl: int = 300):
        """设置缓存，ttl 单位为秒，默认5分钟"""
        with self._lock:
            self._data[key] = {
                "value": value,
                "expires_at": time.time() + ttl
            }

    def delete(self, key: str):
        """删除缓存"""
        with self._lock:
            self._data.pop(key, None)

    def clear(self):
        """清空所有缓存"""
        with self._lock:
            self._data.clear()

    def delete_pattern(self, pattern: str):
        """删除匹配前缀的所有缓存"""
        with self._lock:
            keys_to_delete = [k for k in self._data if k.startswith(pattern)]
            for k in keys_to_delete:
                del self._data[k]

    def make_key(self, *args, **kwargs) -> str:
        """生成缓存键"""
        raw = json.dumps([args, kwargs], ensure_ascii=False, sort_keys=True)
        return hashlib.md5(raw.encode()).hexdigest()


# 全局缓存实例
cache = MemoryCache()


# ============================================================
# LLM 回复缓存
# ============================================================

def get_llm_cache_key(session_id: str, user_input: str) -> str:
    """生成 LLM 回复的缓存键"""
    return f"llm:{session_id}:{hashlib.md5(user_input.encode()).hexdigest()}"


def cache_llm_response(session_id: str, user_input: str, response: str):
    """缓存 LLM 回复，TTL 5分钟"""
    key = get_llm_cache_key(session_id, user_input)
    cache.set(key, response, ttl=300)


def get_cached_llm_response(session_id: str, user_input: str) -> Optional[str]:
    """获取缓存的 LLM 回复"""
    key = get_llm_cache_key(session_id, user_input)
    return cache.get(key)


# ============================================================
# 导师评分缓存
# ============================================================

def get_teacher_score_cache_key(session_id: str) -> str:
    """生成导师评分结果的缓存键"""
    return f"teacher_score:{session_id}"


def cache_teacher_scores(session_id: str, scores: list):
    """缓存导师评分结果，TTL 10分钟"""
    key = get_teacher_score_cache_key(session_id)
    cache.set(key, scores, ttl=600)


def get_cached_teacher_scores(session_id: str) -> Optional[list]:
    """获取缓存的导师评分结果"""
    key = get_teacher_score_cache_key(session_id)
    return cache.get(key)


def invalidate_teacher_scores(session_id: str):
    """画像更新时，清除该用户的导师评分缓存"""
    cache.delete_pattern(f"teacher_score:{session_id}")