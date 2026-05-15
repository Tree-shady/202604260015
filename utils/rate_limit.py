import time
import logging
from collections import defaultdict
from functools import wraps
from typing import Callable, Tuple, Any
from flask import request, jsonify

logger = logging.getLogger(__name__)


class RateLimiter:
    """请求限流器"""
    
    def __init__(self):
        self.requests: defaultdict[str, list[float]] = defaultdict(list)
        self.lockouts: defaultdict[str, dict[str, Any]] = defaultdict(
            lambda: {'count': 0, 'until': 0}
        )

    def is_locked_out(self, key: str) -> bool:
        """检查是否被锁定"""
        return self.lockouts[key]['until'] > time.time()

    def add_failed_attempt(
        self, 
        key: str, 
        lockout_duration: int = 1800, 
        max_attempts: int = 5
    ) -> bool:
        """添加失败尝试，返回是否触发锁定"""
        self.lockouts[key]['count'] += 1
        if self.lockouts[key]['count'] >= max_attempts:
            self.lockouts[key]['until'] = time.time() + lockout_duration
            logger.warning(f"Key {key} has been locked out for {lockout_duration}s")
            return True
        return False

    def reset_attempts(self, key: str) -> None:
        """重置尝试次数"""
        if key in self.lockouts:
            self.lockouts[key]['count'] = 0
            self.lockouts[key]['until'] = 0

    def record_request(self, key: str, window: int = 60, max_requests: int = 60) -> bool:
        """记录请求，返回是否在限制内"""
        now = time.time()
        # 清理过期请求
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        self.requests[key].append(now)
        return len(self.requests[key]) <= max_requests

    def get_remaining(self, key: str, window: int = 60, max_requests: int = 60) -> int:
        """获取剩余请求次数"""
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        return max(0, max_requests - len(self.requests[key]))

    def get_retry_after(self, key: str) -> int:
        """获取重试等待时间（秒）"""
        if key in self.lockouts and self.lockouts[key]['until'] > time.time():
            return int(self.lockouts[key]['until'] - time.time())
        return 0


rate_limiter = RateLimiter()


def rate_limit(max_requests: int = 60, window: int = 60) -> Callable:
    """
    请求限制装饰器
    
    Args:
        max_requests: 时间窗口内最大请求数
        window: 时间窗口（秒）
        
    Returns:
        装饰器函数
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            key = request.remote_addr or 'anonymous'
            
            # 检查是否在开发模式下，如果是则可以放宽限制
            from flask import current_app
            if current_app and current_app.config.get('DEBUG'):
                # 调试模式下放宽限制 x10
                debug_max_requests = max_requests * 10
                if not rate_limiter.record_request(key, window, debug_max_requests):
                    logger.debug(f"Rate limit hit for {key} (debug mode)")
                return f(*args, **kwargs)
            
            if not rate_limiter.record_request(key, window, max_requests):
                remaining = rate_limiter.get_remaining(key, window, max_requests)
                logger.warning(f"Rate limit exceeded for {key}: {max_requests}/{window}s")
                return jsonify({
                    'error': '请求过于频繁，请稍后再试',
                    'message': f'请等待 {window} 秒后重试',
                    'retry_after': window,
                    'remaining': remaining
                }), 429

            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_login_lockout(ip_address: str) -> Tuple[bool, int]:
    """
    检查IP是否被锁定
    
    Args:
        ip_address: IP地址
        
    Returns:
        (是否锁定, 剩余秒数)
    """
    key = f"login:{ip_address}"
    if rate_limiter.is_locked_out(key):
        return True, rate_limiter.get_retry_after(key)
    return False, 0


def record_login_failure(ip_address: str) -> bool:
    """
    记录登录失败
    
    Args:
        ip_address: IP地址
        
    Returns:
        是否触发锁定
    """
    key = f"login:{ip_address}"
    is_locked = rate_limiter.add_failed_attempt(key)
    return is_locked


def reset_login_attempts(ip_address: str) -> None:
    """
    重置登录尝试次数
    
    Args:
        ip_address: IP地址
    """
    key = f"login:{ip_address}"
    rate_limiter.reset_attempts(key)
