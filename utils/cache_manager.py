from flask import current_app
from functools import wraps


class CacheManager:
    """统一缓存管理器"""
    
    @staticmethod
    def get(key, default=None):
        """获取缓存值"""
        try:
            return current_app.cache.get(key)
        except Exception:
            return default
    
    @staticmethod
    def set(key, value, timeout=None):
        """设置缓存值"""
        try:
            current_app.cache.set(key, value, timeout)
            return True
        except Exception:
            return False
    
    @staticmethod
    def delete(key):
        """删除缓存"""
        try:
            current_app.cache.delete(key)
            return True
        except Exception:
            return False
    
    @staticmethod
    def clear():
        """清空所有缓存"""
        try:
            current_app.cache.clear()
            return True
        except Exception:
            return False
    
    @staticmethod
    def get_many(*keys):
        """批量获取缓存"""
        try:
            return current_app.cache.get_many(*keys)
        except Exception:
            return [None] * len(keys)
    
    @staticmethod
    def set_many(mapping, timeout=None):
        """批量设置缓存"""
        try:
            current_app.cache.set_many(mapping, timeout)
            return True
        except Exception:
            return False


def cached(timeout=300, key_prefix='view'):
    """缓存装饰器"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            cache_key = f'{key_prefix}:{f.__name__}'
            try:
                rv = current_app.cache.get(cache_key)
                if rv is None:
                    rv = f(*args, **kwargs)
                    current_app.cache.set(cache_key, rv, timeout)
                return rv
            except Exception:
                return f(*args, **kwargs)
        return decorated_function
    return decorator


cache_manager = CacheManager()
