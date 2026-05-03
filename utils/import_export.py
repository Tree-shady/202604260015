"""
数据导入/导出模块

提供日记数据的导入和导出功能
"""

import json
import csv
import zipfile
from pathlib import Path
from datetime import datetime

def get_db_session():
    """获取数据库会话"""
    from sqlalchemy.orm import sessionmaker
    from .models import engine
    Session = sessionmaker(bind=engine)
    return Session()

def export_to_json(output_file=None):
    """导出日记数据到 JSON 文件"""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"diary_export_{timestamp}.json"
    
    output_path = Path(output_file)
    session = get_db_session()
    
    from .models import Entry, Tag, Mood
    
    data = {
        'export_date': datetime.now().isoformat(),
        'diaries': [],
        'tags': []
    }
    
    entries = session.query(Entry).all()
    for entry in entries:
        mood_info = None
        if entry.mood:
            mood_info = {
                'type': entry.mood.mood_type,
                'note': entry.mood.note
            }
        
        data['diaries'].append({
            'date': entry.date_str,
            'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
            'tags': [t.name for t in entry.tags],
            'content': entry.content,
            'mood': mood_info
        })
    
    data['tags'] = [t.name for t in session.query(Tag).all()]
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path

def export_to_csv(output_file=None):
    """导出日记数据到 CSV 文件"""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"diary_export_{timestamp}.csv"
    
    output_path = Path(output_file)
    session = get_db_session()
    
    from .models import Entry
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Timestamp', 'Mood', 'Tags', 'Content'])
        
        entries = session.query(Entry).all()
        for entry in entries:
            date_str = entry.date_str
            timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M') if entry.timestamp else ''
            mood = entry.mood.mood_type if entry.mood else ''
            tags = ', '.join([t.name for t in entry.tags])
            writer.writerow([date_str, timestamp, mood, tags, entry.content])
    
    return output_path

def export_to_markdown(output_dir=None):
    """导出日记数据到 Markdown 文件"""
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"diary_export_{timestamp}"
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    session = get_db_session()
    
    from .models import Entry
    
    mood_emoji = {'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'}
    mood_labels = {'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'}
    
    entries = session.query(Entry).all()
    for entry in entries:
        date_str = entry.date_str
        timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M') if entry.timestamp else ''
        tags = ', '.join([t.name for t in entry.tags])
        
        mood_display = ''
        if entry.mood:
            mood_type = entry.mood.mood_type
            mood_display = f"{mood_emoji.get(mood_type, '😐')} {mood_labels.get(mood_type, '一般')}"
            if entry.mood.note:
                mood_display += f" - {entry.mood.note}"
        
        md_file = output_path / f"{date_str}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {date_str} 的日记\n\n")
            if timestamp:
                f.write(f"**时间：** {timestamp}\n\n")
            if mood_display:
                f.write(f"**心情：** {mood_display}\n\n")
            if tags:
                f.write(f"**标签：** {tags}\n\n")
            f.write(entry.content)
    
    return output_path

def export_to_zip(output_file=None):
    """导出日记数据到 ZIP 文件"""
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"diary_export_{timestamp}.zip"
    
    output_path = Path(output_file)
    session = get_db_session()
    
    from .models import Entry, Tag
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        entries_data = []
        
        entries = session.query(Entry).all()
        for entry in entries:
            entry_dict = {
                'date': entry.date_str,
                'timestamp': entry.timestamp.isoformat() if entry.timestamp else None,
                'content': entry.content,
                'tags': [t.name for t in entry.tags],
                'mood': None
            }
            if entry.mood:
                entry_dict['mood'] = {
                    'type': entry.mood.mood_type,
                    'note': entry.mood.note
                }
            entries_data.append(entry_dict)
        
        tags_data = [{'name': t.name} for t in session.query(Tag).all()]
        
        export_data = {
            'export_date': datetime.now().isoformat(),
            'diaries': entries_data,
            'tags': tags_data
        }
        
        zf.writestr('diaries.json', json.dumps(export_data, ensure_ascii=False, indent=2))
    
    return output_path
