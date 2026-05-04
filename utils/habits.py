"""
习惯分析模块

分析用户的写作习惯，包括最佳写作时间、热力图等
"""

from datetime import datetime, timedelta
from collections import Counter, defaultdict
from .models import Entry, get_session


def get_writing_heatmap(user_id, year=None):
    """获取写作热力图数据
    
    Args:
        user_id: 用户ID
        year: 年份，默认为今年
    
    Returns:
        dict: 按月份和日期的热力图数据
    """
    if year is None:
        year = datetime.now().year
    
    session = get_session()
    
    entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str.like(f"{year}-%")
    ).all()
    
    heatmap = defaultdict(int)
    for entry in entries:
        date = entry.date_str
        heatmap[date] += len(entry.content)
    
    return dict(heatmap)


def get_best_writing_time(user_id):
    """分析最佳写作时间
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 最佳写作时间分析
    """
    session = get_session()
    
    entries = session.query(Entry).filter_by(user_id=user_id).all()
    
    if not entries:
        return {
            'hourly_dist': {},
            'day_of_week_dist': {},
            'best_hour': None,
            'best_day': None,
            'avg_entries_per_day': 0
        }
    
    # 按小时统计
    hourly = Counter()
    # 按星期统计 (0=周一, 6=周日)
    daily = Counter()
    
    for entry in entries:
        try:
            dt = datetime.strptime(entry.date_str, "%Y-%m-%d")
            hour = dt.hour
            weekday = dt.weekday()
            
            hourly[hour] += 1
            daily[weekday] += 1
        except:
            pass
    
    # 找出最佳时间
    best_hour = hourly.most_common(1)[0][0] if hourly else None
    best_day = daily.most_common(1)[0][0] if daily else None
    
    day_names = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    
    # 计算平均每天写日记次数
    if entries:
        dates = set(e.date_str for e in entries)
        avg_per_day = len(entries) / max(len(dates), 1)
    else:
        avg_per_day = 0
    
    return {
        'hourly_dist': dict(hourly),
        'day_of_week_dist': {day_names[k]: v for k, v in daily.items()},
        'best_hour': best_hour,
        'best_day': day_names[best_day] if best_day is not None else None,
        'avg_entries_per_day': round(avg_per_day, 2)
    }


def get_writing_streak_analysis(user_id):
    """分析连续写作情况
    
    Args:
        user_id: 用户ID
    
    Returns:
        dict: 连续写作分析
    """
    session = get_session()
    
    entries = session.query(Entry).filter_by(user_id=user_id).order_by(Entry.date_str).all()
    
    if not entries:
        return {
            'current_streak': 0,
            'longest_streak': 0,
            'total_active_days': 0,
            'completion_rate': 0
        }
    
    entry_dates = sorted(set(e.date_str for e in entries))
    
    # 计算当前连续
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    current_streak = 0
    if today in entry_dates or yesterday in entry_dates:
        start_date = today if today in entry_dates else yesterday
        current_streak = 1
        current_date = datetime.strptime(start_date, "%Y-%m-%d")
        
        while True:
            current_date -= timedelta(days=1)
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in entry_dates:
                current_streak += 1
            else:
                break
    
    # 计算最长连续
    longest_streak = 1
    current = 1
    for i in range(1, len(entry_dates)):
        d1 = datetime.strptime(entry_dates[i], "%Y-%m-%d")
        d2 = datetime.strptime(entry_dates[i-1], "%Y-%m-%d")
        if (d1 - d2).days == 1:
            current += 1
            longest_streak = max(longest_streak, current)
        else:
            current = 1
    
    # 计算坚持率
    if entry_dates:
        first_date = datetime.strptime(entry_dates[0], "%Y-%m-%d")
        last_date = datetime.strptime(entry_dates[-1], "%Y-%m-%d")
        total_days = (last_date - first_date).days + 1
        completion_rate = len(entry_dates) / total_days * 100 if total_days > 0 else 0
    else:
        completion_rate = 0
    
    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'total_active_days': len(entry_dates),
        'completion_rate': round(completion_rate, 1)
    }


def get_monthly_completion(user_id, year=None):
    """获取每月完成情况
    
    Args:
        user_id: 用户ID
        year: 年份
    
    Returns:
        dict: 每月完成情况
    """
    if year is None:
        year = datetime.now().year
    
    session = get_session()
    
    entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str.like(f"{year}-%")
    ).all()
    
    monthly = defaultdict(int)
    for entry in entries:
        month = int(entry.date_str[5:7])
        monthly[month] += 1
    
    month_names = ['1月', '2月', '3月', '4月', '5月', '6月', 
                   '7月', '8月', '9月', '10月', '11月', '12月']
    
    return {month_names[k-1]: v for k, v in monthly.items()}


def get_year_summary(user_id, year=None):
    """获取年度总结
    
    Args:
        user_id: 用户ID
        year: 年份
    
    Returns:
        dict: 年度总结数据
    """
    if year is None:
        year = datetime.now().year
    
    session = get_session()
    
    entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str.like(f"{year}-%")
    ).all()
    
    if not entries:
        return None
    
    total_chars = sum(len(e.content) for e in entries)
    avg_chars = total_chars // len(entries) if entries else 0
    
    # 按月统计
    monthly = defaultdict(int)
    for entry in entries:
        month = int(entry.date_str[5:7])
        monthly[month] += 1
    
    return {
        'total_entries': len(entries),
        'total_chars': total_chars,
        'avg_chars': avg_chars,
        'most_active_month': max(monthly.items(), key=lambda x: x[1])[0] if monthly else None,
        'entries_per_month': dict(monthly)
    }
