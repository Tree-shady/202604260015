"""
限流管理工具 - 用于调试和管理限流状态
"""
import time
from typing import Dict, Any, List, Tuple
from utils.rate_limit import rate_limiter


def get_rate_limit_status() -> Dict[str, Any]:
    """
    获取当前限流状态
    
    Returns:
        包含限流状态的字典
    """
    now = time.time()
    status = {
        'active_request_limits': {},
        'active_lockouts': {},
        'timestamp': now
    }
    
    # 收集请求限制状态
    for key, times in rate_limiter.requests.items():
        # 只保留最近60秒的请求
        recent_times = [t for t in times if now - t < 60]
        if recent_times:
            status['active_request_limits'][key] = {
                'count': len(recent_times),
                'oldest': now - min(recent_times) if recent_times else 0
            }
    
    # 收集锁定状态
    for key, lockout in rate_limiter.lockouts.items():
        if lockout['until'] > now:
            status['active_lockouts'][key] = {
                'count': lockout['count'],
                'remaining': int(lockout['until'] - now)
            }
    
    return status


def reset_rate_limit(key: str) -> bool:
    """
    重置特定键的限流状态
    
    Args:
        key: 要重置的键
        
    Returns:
        是否成功重置
    """
    if key in rate_limiter.requests:
        rate_limiter.requests[key] = []
    
    if key in rate_limiter.lockouts:
        rate_limiter.lockouts[key]['count'] = 0
        rate_limiter.lockouts[key]['until'] = 0
    
    return True


def reset_all_rate_limits() -> int:
    """
    重置所有限流状态
    
    Returns:
        重置的键数量
    """
    count = len(rate_limiter.requests) + len(rate_limiter.lockouts)
    rate_limiter.requests.clear()
    rate_limiter.lockouts.clear()
    return count


def print_rate_limit_status() -> None:
    """打印当前限流状态（用于调试）"""
    status = get_rate_limit_status()
    
    print("\n" + "=" * 60)
    print("限流状态")
    print("=" * 60)
    
    if status['active_request_limits']:
        print("\n活跃请求限制:")
        for key, info in status['active_request_limits'].items():
            print(f"  {key}: {info['count']} 次请求 (最旧 {info['oldest']:.1f}s 前)")
    else:
        print("\n无活跃请求限制")
    
    if status['active_lockouts']:
        print("\n活跃锁定:")
        for key, info in status['active_lockouts'].items():
            print(f"  {key}: {info['count']} 次尝试, 剩余 {info['remaining']}s")
    else:
        print("\n无活跃锁定")
    
    print("\n" + "=" * 60 + "\n")
