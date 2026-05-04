"""
年度回顾模块

自动生成个人年度成长报告
"""

from datetime import datetime
from collections import Counter, defaultdict
from .models import Entry, Mood, Tag, get_session
from .config import DATE_FORMAT


def get_yearly_review(user_id, year=None):
    """生成年度回顾报告
    
    Args:
        user_id: 用户ID
        year: 年份，默认为今年
    
    Returns:
        dict: 年度回顾数据
    """
    if year is None:
        year = datetime.now().year
    
    session = get_session()
    
    # 获取该年的所有日记
    entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str.like(f"{year}-%")
    ).all()
    
    if not entries:
        return {
            'year': year,
            'total_entries': 0,
            'has_data': False
        }
    
    # 基础统计
    total_entries = len(entries)
    total_chars = sum(len(e.content) for e in entries)
    avg_chars = int(total_chars / total_entries) if total_entries > 0 else 0
    
    # 心情统计
    mood_data = defaultdict(int)
    for entry in entries:
        if entry.mood:
            mood_data[entry.mood.mood_type] += 1
    
    # 标签统计
    tag_count = Counter()
    for entry in entries:
        for tag in entry.tags:
            tag_count[tag.name] += 1
    top_tags = tag_count.most_common(10)
    
    # 月度分布
    monthly_dist = defaultdict(int)
    for entry in entries:
        month = int(entry.date_str[5:7])
        monthly_dist[month] += 1
    
    # 找出写日记最多的月份
    best_month = None
    max_count = 0
    for month, count in monthly_dist.items():
        if count > max_count:
            max_count = count
            best_month = month
    
    # 最长日记
    longest_entry = None
    max_content_length = 0
    for entry in entries:
        if len(entry.content) > max_content_length:
            max_content_length = len(entry.content)
            longest_entry = entry
    
    # 首次写日记和最后一次
    entry_dates = sorted([e.date_str for e in entries])
    first_entry = entry_dates[0]
    last_entry = entry_dates[-1]
    
    # 生成年度总结词
    summary_words = generate_yearly_summary(mood_data, total_entries)
    
    return {
        'year': year,
        'total_entries': total_entries,
        'total_chars': total_chars,
        'avg_chars': avg_chars,
        'has_data': True,
        'mood_data': mood_data,
        'top_tags': top_tags,
        'monthly_dist': monthly_dist,
        'best_month': best_month,
        'best_month_count': max_count,
        'longest_entry': {
            'date': longest_entry.date_str if longest_entry else None,
            'length': max_content_length
        },
        'first_entry': first_entry,
        'last_entry': last_entry,
        'summary_words': summary_words
    }


def generate_yearly_summary(mood_data, total_entries):
    """生成年度总结关键词
    
    Args:
        mood_data: 心情统计数据
        total_entries: 总日记数
    
    Returns:
        list: 总结关键词
    """
    summary = []
    
    # 根据心情添加关键词
    total_moods = sum(mood_data.values())
    if total_moods > 0:
        happy_ratio = mood_data.get('happy', 0) + mood_data.get('excited', 0)
        calm_ratio = mood_data.get('calm', 0)
        sad_ratio = mood_data.get('sad', 0) + mood_data.get('anxious', 0)
        
        if happy_ratio / total_moods > 0.5:
            summary.extend(['阳光', '快乐', '积极'])
        elif sad_ratio / total_moods > 0.4:
            summary.extend(['成长', '反思', '坚强'])
        elif calm_ratio / total_moods > 0.5:
            summary.extend(['平静', '专注', '踏实'])
    
    # 根据日记数量添加关键词
    if total_entries >= 300:
        summary.extend(['坚持', '毅力', '传奇'])
    elif total_entries >= 200:
        summary.extend(['自律', '优秀'])
    elif total_entries >= 100:
        summary.extend(['不错', '坚持'])
    elif total_entries >= 50:
        summary.extend(['开始', '成长'])
    
    return summary if summary else ['记录', '生活']


def get_comparative_stats(user_id, year1, year2):
    """对比两年的数据
    
    Args:
        user_id: 用户ID
        year1: 第一年
        year2: 第二年
    
    Returns:
        dict: 对比数据
    """
    review1 = get_yearly_review(user_id, year1)
    review2 = get_yearly_review(user_id, year2)
    
    return {
        'year1': review1,
        'year2': review2
    }


def get_monthly_word_cloud(user_id, year):
    """获取月度词频数据（简化版）
    
    Args:
        user_id: 用户ID
        year: 年份
    
    Returns:
        dict: 按月份的关键词
    """
    session = get_session()
    
    entries = session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date_str.like(f"{year}-%")
    ).all()
    
    monthly_tags = defaultdict(list)
    for entry in entries:
        month = int(entry.date_str[5:7])
        for tag in entry.tags:
            monthly_tags[month].append(tag.name)
    
    # 简单提取每个月最常用的标签
    monthly_top = {}
    for month, tags in monthly_tags.items():
        tag_cnt = Counter(tags)
        monthly_top[month] = tag_cnt.most_common(3)
    
    return monthly_top
