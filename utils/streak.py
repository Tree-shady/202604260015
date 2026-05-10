"""
连续打卡模块

提供连续写日记的统计和激励功能
"""

import logging
from datetime import datetime, timedelta
from .config import DATE_FORMAT
from .models import User, Entry, get_session

logger = logging.getLogger(__name__)


def get_yesterday_str():
    """获取昨天的日期字符串"""
    yesterday = datetime.now() - timedelta(days=1)
    return yesterday.strftime(DATE_FORMAT)


def get_today_str():
    """获取今天的日期字符串"""
    return datetime.now().strftime(DATE_FORMAT)


def is_consecutive(date1, date2):
    """判断两个日期是否连续
    
    Args:
        date1: 较晚的日期
        date2: 较早的日期
    
    Returns:
        bool: date2 是否是 date1 的前一天
    """
    try:
        d1 = datetime.strptime(date1, DATE_FORMAT)
        d2 = datetime.strptime(date2, DATE_FORMAT)
        delta = d1 - d2
        return delta.days == 1
    except ValueError:
        return False


def update_streak_on_entry(user_id, entry_date):
    """写日记时更新连续打卡统计
    
    Args:
        user_id: 用户ID
        entry_date: 日记日期
    """
    session = get_session()
    
    try:
        user = session.query(User).filter_by(id=user_id).first()
        if not user:
            return
        
        # 直接查询日期字段，避免加载完整对象
        entry_dates = set()
        results = session.query(Entry.date_str).filter_by(user_id=user_id).all()
        for row in results:
            entry_dates.add(row[0])
        entry_dates.add(entry_date)  # 包含今天的新日记
        
        # 计算当前连续打卡天数
        current_streak = calculate_current_streak(entry_dates)
        
        # 计算最长连续打卡天数
        longest_streak = calculate_longest_streak(entry_dates)
        
        # 更新用户信息
        user.current_streak = current_streak
        user.longest_streak = longest_streak
        user.last_entry_date = entry_date
        user.total_entries = len(entry_dates)
        
        session.commit()
        
        return {
            'current_streak': current_streak,
            'longest_streak': longest_streak,
            'total_entries': len(entry_dates)
        }
    except Exception as e:
        session.rollback()
        logger.error(f"更新打卡统计时出错: {e}")
        return None


def calculate_current_streak(entry_dates):
    """计算当前连续打卡天数
    
    Args:
        entry_dates: 所有有日记的日期集合
    
    Returns:
        int: 当前连续打卡天数
    """
    if not entry_dates:
        return 0
    
    sorted_dates = sorted(entry_dates, reverse=True)
    today = get_today_str()
    yesterday = get_yesterday_str()
    
    # 从最新日期开始向前数连续的天数
    streak = 0
    current_date = None
    
    # 找到起始点（今天或昨天）
    if today in sorted_dates:
        current_date = today
        streak = 1
    elif yesterday in sorted_dates:
        current_date = yesterday
        streak = 1
    else:
        return 0
    
    # 继续向前找连续的日期
    for date in sorted_dates:
        if date == current_date:
            continue
        if is_consecutive(current_date, date):
            streak += 1
            current_date = date
        else:
            break
    
    return streak


def calculate_longest_streak(entry_dates):
    """计算历史最长连续打卡天数
    
    Args:
        entry_dates: 所有有日记的日期集合
    
    Returns:
        int: 最长连续打卡天数
    """
    if not entry_dates:
        return 0
    
    sorted_dates = sorted(entry_dates)
    longest = 1
    current = 1
    
    for i in range(1, len(sorted_dates)):
        if is_consecutive(sorted_dates[i], sorted_dates[i-1]):
            current += 1
            if current > longest:
                longest = current
        else:
            current = 1
    
    return longest


def get_user_streak_info(user_id):
    """获取用户的打卡统计信息
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 打卡信息
    """
    session = get_session()
    user = session.query(User).filter_by(id=user_id).first()
    
    if not user:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'total_entries': 0,
            'last_entry_date': None
        }
    
    return {
        'current_streak': user.current_streak,
        'longest_streak': user.longest_streak,
        'total_entries': user.total_entries,
        'last_entry_date': user.last_entry_date
    }


def get_streak_message(current_streak, longest_streak):
    """根据打卡天数返回激励消息
    
    Args:
        current_streak: 当前连续天数
        longest_streak: 最长连续天数
    
    Returns:
        str: 激励消息
    """
    messages = [
        (1, "🎉 太棒了！新的开始！"),
        (3, "🔥 很好，开始有规律了！"),
        (7, "🌟 一周了！真了不起！"),
        (14, "💫 两周！你真的很坚持！"),
        (30, "🏆 一个月！里程碑时刻！"),
        (50, "👑 50天！超级有毅力！"),
        (100, "💎 100天！传奇成就！"),
    ]
    
    # 查找对应的消息
    for threshold, message in reversed(messages):
        if current_streak >= threshold:
            return message
    
    return "✍️ 开始记录你的每一天吧！"


def get_streak_reward(current_streak):
    """获取打卡天数对应的成就徽章
    
    Args:
        current_streak: 当前连续天数
    
    Returns:
        list: 获得的徽章列表
    """
    badges = []
    thresholds = [
        (1, "初次尝试", "🌱"),
        (3, "小有规律", "⭐"),
        (7, "坚持一周", "🌟"),
        (14, "两周达人", "💫"),
        (30, "月度之星", "🏆"),
        (50, "坚持达人", "👑"),
        (100, "百日传奇", "💎"),
    ]
    
    for threshold, name, emoji in thresholds:
        if current_streak >= threshold:
            badges.append({'name': name, 'emoji': emoji})
    
    return badges


def recalculate_all_user_streaks():
    """重新计算所有用户的打卡统计（数据库迁移用）"""
    session = get_session()
    
    users = session.query(User).all()
    
    for user in users:
        # 获取该用户所有日记日期
        entries = session.query(Entry).filter_by(user_id=user.id).all()
        entry_dates = set(e.date_str for e in entries)
        
        if entry_dates:
            current_streak = calculate_current_streak(entry_dates)
            longest_streak = calculate_longest_streak(entry_dates)
            
            user.current_streak = current_streak
            user.longest_streak = longest_streak
            user.total_entries = len(entry_dates)
            
            # 找出最后写日记的日期
            if entry_dates:
                user.last_entry_date = max(entry_dates)
        else:
            user.current_streak = 0
            user.longest_streak = 0
            user.total_entries = 0
            user.last_entry_date = None
    
    session.commit()
