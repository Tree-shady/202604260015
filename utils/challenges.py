"""
挑战系统模块

提供写作挑战功能
"""

from datetime import datetime, timedelta
from .models import User, Entry, get_session


CHALLENGES = {
    '7days': {
        'name': '7天挑战',
        'days': 7,
        'description': '连续7天写日记',
        'badge': '🌟'
    },
    '30days': {
        'name': '30天挑战',
        'days': 30,
        'description': '连续30天写日记，养成好习惯',
        'badge': '🏆'
    },
    '100days': {
        'name': '100天挑战',
        'days': 100,
        'description': '连续100天写日记，传奇成就',
        'badge': '💎'
    },
    '365days': {
        'name': '365天挑战',
        'days': 365,
        'description': '连续一年写日记，永恒的坚持',
        'badge': '👑'
    }
}


def start_challenge(user_id, challenge_id):
    """开始一个挑战
    
    Args:
        user_id: 用户ID
        challenge_id: 挑战ID
    
    Returns:
        dict: 挑战信息
    """
    if challenge_id not in CHALLENGES:
        return None
    
    challenge = CHALLENGES[challenge_id]
    
    session = get_session()
    user = session.query(User).filter_by(id=user_id).first()
    
    if not user:
        return None
    
    # 检查是否已经有进行中的挑战
    current_challenge = get_active_challenge(user_id)
    if current_challenge:
        return {
            'has_active': True,
            'challenge': current_challenge
        }
    
    # 计算挑战结束日期
    start_date = datetime.now()
    end_date = start_date + timedelta(days=challenge['days'])
    
    challenge_data = {
        'challenge_id': challenge_id,
        'name': challenge['name'],
        'badge': challenge['badge'],
        'start_date': start_date.strftime("%Y-%m-%d"),
        'end_date': end_date.strftime("%Y-%m-%d"),
        'days': challenge['days'],
        'description': challenge['description'],
        'completed': False
    }
    
    # 存储到用户设置
    from utils.settings import set_user_setting, get_user_setting
    set_user_setting(user_id, 'active_challenge', challenge_data)
    
    return {
        'has_active': False,
        'challenge': challenge_data
    }


def get_active_challenge(user_id):
    """获取当前进行中的挑战
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 挑战信息，如果无进行中挑战则返回None
    """
    from utils.settings import get_user_setting
    
    challenge_data = get_user_setting(user_id, 'active_challenge', None)
    
    if not challenge_data:
        return None
    
    # 检查挑战是否过期
    end_date = datetime.strptime(challenge_data['end_date'], "%Y-%m-%d")
    if datetime.now() > end_date:
        # 挑战过期，检查是否完成
        if not challenge_data.get('completed'):
            # 挑战失败
            return None
    
    # 计算进度
    start_date = datetime.strptime(challenge_data['start_date'], "%Y-%m-%d")
    days_passed = (datetime.now() - start_date).days + 1
    challenge_data['days_passed'] = days_passed
    challenge_data['progress'] = min(100, int(days_passed / challenge_data['days'] * 100))
    
    # 检查今日是否已写日记
    today = datetime.now().strftime("%Y-%m-%d")
    session = get_session()
    today_entry = session.query(Entry).filter_by(
        user_id=user_id,
        date_str=today
    ).first()
    
    challenge_data['wrote_today'] = today_entry is not None
    
    return challenge_data


def check_challenge_completion(user_id):
    """检查挑战是否完成
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 完成结果
    """
    from utils.settings import get_user_setting, set_user_setting
    
    challenge_data = get_active_challenge(user_id)
    
    if not challenge_data:
        return None
    
    # 如果挑战已经标记为完成，直接返回
    if challenge_data.get('completed'):
        return challenge_data
    
    challenge_id = challenge_data['challenge_id']
    days = CHALLENGES[challenge_id]['days']
    
    # 获取挑战时间范围
    start_date = datetime.strptime(challenge_data['start_date'], "%Y-%m-%d")
    end_date = datetime.strptime(challenge_data['end_date'], "%Y-%m-%d")
    
    session = get_session()
    
    # 获取挑战期间的所有日记
    entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str >= challenge_data['start_date'],
        Entry.date_str <= challenge_data['end_date']
    ).order_by(Entry.date_str).all()
    
    if not entries:
        return None
    
    # 提取日期并去重
    entry_dates = sorted(set(e.date_str for e in entries))
    
    # 找到在挑战期间的最长连续
    max_challenge_streak = 0
    current_challenge_streak = 0
    
    # 从开始日期逐天检查
    current_check_date = start_date
    while current_check_date <= end_date:
        date_str = current_check_date.strftime("%Y-%m-%d")
        if date_str in entry_dates:
            current_challenge_streak += 1
            max_challenge_streak = max(max_challenge_streak, current_challenge_streak)
        else:
            current_challenge_streak = 0
        current_check_date += timedelta(days=1)
    
    # 如果最长连续超过或等于要求天数，挑战完成
    if max_challenge_streak >= days:
        # 挑战完成
        challenge_data['completed'] = True
        challenge_data['completed_date'] = datetime.now().strftime("%Y-%m-%d")
        set_user_setting(user_id, 'active_challenge', challenge_data)
        
        # 添加完成记录
        completed_challenges = get_user_setting(user_id, 'completed_challenges', [])
        completed_challenges.append(challenge_data)
        set_user_setting(user_id, 'completed_challenges', completed_challenges)
        
        return challenge_data
    
    return None


def abandon_challenge(user_id):
    """放弃当前挑战
    
    Args:
        user_id: 用户ID
    """
    from utils.settings import set_user_setting
    set_user_setting(user_id, 'active_challenge', None)


def get_completed_challenges(user_id):
    """获取已完成的挑战列表
    
    Args:
        user_id: 用户ID
    
    Returns:
        list: 已完成挑战列表
    """
    from utils.settings import get_user_setting
    return get_user_setting(user_id, 'completed_challenges', [])


def get_all_challenges_status(user_id):
    """获取所有挑战的状态
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 所有挑战状态
    """
    session = get_session()
    entries = session.query(Entry).filter_by(user_id=user_id).all()
    entry_dates = set(e.date_str for e in entries)
    
    result = {
        'active_challenge': get_active_challenge(user_id),
        'completed_challenges': get_completed_challenges(user_id),
        'available_challenges': []
    }
    
    # 检查每个挑战是否可以开始
    today = datetime.now().strftime("%Y-%m-%d")
    
    for cid, challenge in CHALLENGES.items():
        is_completed = any(
            c.get('challenge_id') == cid and c.get('completed')
            for c in result['completed_challenges']
        )
        
        if is_completed:
            status = 'completed'
        elif result['active_challenge'] and result['active_challenge'].get('challenge_id') == cid:
            status = 'active'
        else:
            status = 'available'
        
        result['available_challenges'].append({
            'id': cid,
            'name': challenge['name'],
            'days': challenge['days'],
            'badge': challenge['badge'],
            'description': challenge['description'],
            'status': status
        })
    
    return result
