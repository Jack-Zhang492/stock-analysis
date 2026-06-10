"""
磁盘缓存模块 — 基于 diskcache
"""
import functools
import hashlib
import json
from pathlib import Path

import diskcache

from config import CACHE_DIR, CACHE_TTL


class CacheManager:
    """统一缓存管理器"""

    def __init__(self, cache_dir: Path = CACHE_DIR):
        self.cache = diskcache.Cache(str(cache_dir))

    def _make_key(self, prefix: str, *args, **kwargs) -> str:
        """生成缓存键"""
        raw = f"{prefix}:{json.dumps(args, sort_keys=True, default=str)}:{json.dumps(kwargs, sort_keys=True, default=str)}"
        return hashlib.md5(raw.encode()).hexdigest()

    def get(self, key: str):
        """读取缓存"""
        return self.cache.get(key)

    def set(self, key: str, value, ttl: int = 300):
        """写入缓存"""
        self.cache.set(key, value, expire=ttl)

    def delete(self, key: str):
        """删除缓存"""
        self.cache.delete(key)

    def clear_prefix(self, prefix: str):
        """清除特定前缀的所有缓存"""
        # diskcache 不支持前缀删除，遍历删除
        for key in list(self.cache.iterkeys()):
            if key.startswith(prefix):
                self.cache.delete(key)

    def close(self):
        self.cache.close()


# 全局缓存实例
_cache = CacheManager()


def cached(prefix: str, ttl_key: str = "realtime_quote"):
    """
    缓存装饰器
    用法: @cached("kline", "kline_daily")
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            ttl = CACHE_TTL.get(ttl_key, 300)
            key = _cache._make_key(prefix, *args, **kwargs)
            result = _cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            if result is not None and not (isinstance(result, dict) and result.get("_error")):
                _cache.set(key, result, ttl)
            return result
        return wrapper
    return decorator


def get_cache() -> CacheManager:
    return _cache
