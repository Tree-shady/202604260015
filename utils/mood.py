"""
心情追踪模块

提供心情数据的管理和存储功能
"""

from datetime import datetime
from .config import DATE_FORMAT
from .models import get_session, Mood, Entry

# 心情类型定义
MOOD_TYPES = {
    'happy': {'label': '开心', 'emoji': '😊', 'color': '#4CAF50'},
    'excited': {'label': '兴奋', 'emoji': '🤩', 'color': '#FF9800'},
    'calm': {'label': '平静', 'emoji': '😌', 'color': '#2196F3'},
    'tired': {'label': '疲惫', 'emoji': '😴', 'color': '#9E9E9E'},
    'sad': {'label': '难过', 'emoji': '😢', 'color': '#673AB7'},
    'angry': {'label': '生气', 'emoji': '😠', 'color': '#F44336'},
    'anxious': {'label': '焦虑', 'emoji': '😰', 'color': '#FFC107'},
    'neutral': {'label': '一般', 'emoji': '😐', 'color': '#607D8B'}
}

def get_mood(date_str):
    """获取指定日期的心情
    
    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
    
    Returns:
        dict: 心情数据，包含 mood_type 和 note
    """
    session = get_session()
    entry = session.query(Entry).filter_by(date_str=date_str).first()
    if entry and entry.mood:
        return {
            'mood_type': entry.mood.mood_type,
            'note': entry.mood.note
        }
    return {'mood_type': 'neutral', 'note': ''}

def save_mood(date_str, mood_type, note=''):
    """保存指定日期的心情
    
    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
        mood_type: 心情类型
        note: 心情备注
    """
    session = get_session()
    entry = session.query(Entry).filter_by(date_str=date_str).first()
    if entry:
        if entry.mood:
            entry.mood.mood_type = mood_type
            entry.mood.note = note
        else:
            mood = Mood(
                entry_id=entry.id,
                mood_type=mood_type,
                note=note
            )
            session.add(mood)
        session.commit()

def get_mood_stats(start_date=None, end_date=None):
    """获取心情统计数据
    
    Args:
        start_date: 开始日期，格式 YYYY-MM-DD
        end_date: 结束日期，格式 YYYY-MM-DD
    
    Returns:
        dict: 心情统计数据
    """
    session = get_session()
    
    # 构建查询
    query = session.query(Mood).join(Entry)
    if start_date:
        query = query.filter(Entry.date_str >= start_date)
    if end_date:
        query = query.filter(Entry.date_str <= end_date)
    
    moods = query.all()
    
    # 构建心情数据字典
    filtered_moods = {}
    for mood in moods:
        entry = session.query(Entry).filter_by(id=mood.entry_id).first()
        if entry:
            filtered_moods[entry.date_str] = {
                'mood_type': mood.mood_type,
                'note': mood.note,
                'timestamp': mood.created_at.isoformat()
            }
    
    # 统计各心情类型的数量
    mood_counts = {}
    for mood_data in filtered_moods.values():
        mood_type = mood_data.get('mood_type', 'neutral')
        mood_counts[mood_type] = mood_counts.get(mood_type, 0) + 1
    
    # 计算平均心情指数（1-5分）
    mood_scores = {
        'happy': 5,
        'excited': 5,
        'calm': 4,
        'neutral': 3,
        'tired': 2,
        'anxious': 2,
        'sad': 1,
        'angry': 1
    }
    
    total_score = 0
    for mood_data in filtered_moods.values():
        mood_type = mood_data.get('mood_type', 'neutral')
        total_score += mood_scores.get(mood_type, 3)
    
    avg_score = total_score / len(filtered_moods) if filtered_moods else 0
    
    return {
        'total_days': len(filtered_moods),
        'mood_counts': mood_counts,
        'average_score': round(avg_score, 1),
        'moods': filtered_moods
    }

def get_mood_trend(days=30):
    """获取最近几天的心情趋势
    
    Args:
        days: 天数
    
    Returns:
        list: 心情趋势数据
    """
    end_date = datetime.now().strftime(DATE_FORMAT)
    start_date = (datetime.now() - datetime.timedelta(days=days-1)).strftime(DATE_FORMAT)
    
    stats = get_mood_stats(start_date, end_date)
    
    # 生成日期范围内的所有日期
    trend = []
    current_date = datetime.strptime(start_date, DATE_FORMAT)
    end = datetime.strptime(end_date, DATE_FORMAT)
    
    while current_date <= end:
        date_str = current_date.strftime(DATE_FORMAT)
        mood_data = stats['moods'].get(date_str, {'mood_type': 'neutral'})
        
        trend.append({
            'date': date_str,
            'mood_type': mood_data['mood_type'],
            'mood_info': MOOD_TYPES.get(mood_data['mood_type'], MOOD_TYPES['neutral'])
        })
        
        current_date += datetime.timedelta(days=1)
    
    return trend
