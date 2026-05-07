import time
from collections import defaultdict
from functools import wraps
from flask import request, jsonify, current_app

class RateLimiter:
    def __init__(self):
        self.requests = defaultdict(list)
        self.lockouts = defaultdict(lambda: {'count': 0, 'until': 0})

    def is_locked_out(self, key):
        if self.lockouts[key]['until'] > time.time():
            return True
        return False

    def add_failed_attempt(self, key, lockout_duration=1800, max_attempts=5):
        self.lockouts[key]['count'] += 1
        if self.lockouts[key]['count'] >= max_attempts:
            self.lockouts[key]['until'] = time.time() + lockout_duration
            return True
        return False

    def reset_attempts(self, key):
        if key in self.lockouts:
            self.lockouts[key]['count'] = 0
            self.lockouts[key]['until'] = 0

    def record_request(self, key, window=60, max_requests=60):
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        self.requests[key].append(now)
        return len(self.requests[key]) <= max_requests

    def get_remaining(self, key, window=60, max_requests=60):
        now = time.time()
        self.requests[key] = [t for t in self.requests[key] if now - t < window]
        return max(0, max_requests - len(self.requests[key]))

    def get_retry_after(self, key):
        if key in self.lockouts and self.lockouts[key]['until'] > time.time():
            return int(self.lockouts[key]['until'] - time.time())
        return 0

rate_limiter = RateLimiter()

def rate_limit(max_requests=60, window=60):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            key = request.remote_addr or 'anonymous'

            if not rate_limiter.record_request(key, window, max_requests):
                return jsonify({
                    'error': '请求过于频繁，请稍后再试',
                    'retry_after': window
                }), 429

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def check_login_lockout(ip_address):
    """检查IP是否被锁定，返回(是否锁定, 剩余秒数)"""
    key = f"login:{ip_address}"
    if rate_limiter.is_locked_out(key):
        return True, rate_limiter.get_retry_after(key)
    return False, 0

def record_login_failure(ip_address):
    """记录登录失败"""
    key = f"login:{ip_address}"
    is_locked = rate_limiter.add_failed_attempt(key)
    return is_locked

def reset_login_attempts(ip_address):
    """重置登录尝试次数"""
    key = f"login:{ip_address}"
    rate_limiter.reset_attempts(key)
