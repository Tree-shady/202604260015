"""
回忆模块

提供"去年的今天"等回忆功能
"""

from datetime import datetime, timedelta
from collections import Counter
from .models import Entry, get_session


def get_memories(user_id):
    """获取回忆数据
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 包含各种回忆数据
    """
    session = get_session()
    today = datetime.now()
    today_str = today.strftime("%Y-%m-%d")
    
    # 获取今年今天的所有日记
    this_year_entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str == today_str
    ).all()
    
    # 获取去年今天的日记
    try:
        last_year_date = today.replace(year=today.year - 1).strftime("%Y-%m-%d")
    except ValueError:
        last_year_date = today.replace(year=today.year - 1, day=28).strftime("%Y-%m-%d")
    last_year_entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str == last_year_date
    ).all()
    
    # 获取去年同月的日记
    last_year_month_start = today.replace(year=today.year - 1, day=1).strftime("%Y-%m-%d")[:7]
    last_year_month_entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str.like(f"{last_year_month_start}%")
    ).all()
    
    memories = {
        'this_year_today': this_year_entries,
        'last_year_today': last_year_entries,
        'last_year_same_month': last_year_month_entries,
        'today_str': today_str,
        'last_year_date': last_year_date,
        'years_ago': 1
    }
    
    return memories


def get_same_day_last_years(user_id, years=5):
    """获取过去多年的同一天日记
    
    Args:
        user_id: 用户ID
        years: 往前追溯的年数
    
    Returns:
        dict: {年份: [entries]}
    """
    session = get_session()
    today = datetime.now()
    
    result = {}
    for i in range(1, years + 1):
        try:
            # 使用 replace 方法替换年份，处理闰年
            target_date = today.replace(year=today.year - i)
        except ValueError:
            # 处理 2月29日的情况，该年不是闰年时改为 2月28日
            target_date = today.replace(year=today.year - i, day=28)
        
        target_str = target_date.strftime("%Y-%m-%d")
        
        entries = session.query(Entry).filter(
            Entry.user_id == user_id,
            Entry.date_str == target_str
        ).all()
        
        if entries:
            result[target_date.year] = entries
    
    return result


def get_milestone_entries(user_id):
    """获取里程碑日记（首次、100篇、365篇等）
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 里程碑数据
    """
    session = get_session()
    
    entries = session.query(Entry).filter_by(user_id=user_id).order_by(Entry.date_str).all()
    
    milestones = {
        'first_entry': entries[0] if entries else None,
        'total_entries': len(entries)
    }
    
    # 检查特殊数字的日记
    special_numbers = [10, 50, 100, 200, 365, 500, 1000]
    for num in special_numbers:
        if len(entries) >= num:
            milestones[f'{num}_th_entry'] = entries[num - 1]
    
    return milestones


def get_memories_for_date(user_id, date_str):
    """获取特定日期的回忆
    
    Args:
        user_id: 用户ID
        date_str: 日期字符串 (YYYY-MM-DD)
    
    Returns:
        dict: 该日期在不同年份的情况
    """
    session = get_session()
    result = {}
    
    try:
        target_date = datetime.strptime(date_str, "%Y-%m-%d")
        
        for i in range(0, 6):
            check_date = target_date - timedelta(days=365 * i)
            check_str = check_date.strftime("%Y-%m-%d")
            
            entries = session.query(Entry).filter(
                Entry.user_id == user_id,
                Entry.date_str == check_str
            ).all()
            
            if entries:
                result[check_date.year] = {
                    'date': check_str,
                    'entries': entries,
                    'years_ago': i
                }
    except ValueError:
        pass
    
    return result
