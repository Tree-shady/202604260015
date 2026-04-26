"""
统计和导出模块

提供日记统计信息和导出功能
"""

from pathlib import Path
from datetime import datetime, timedelta
from .config import ENTRIES_DIR

def get_diary_stats():
    """获取日记统计信息"""
    entries = list(ENTRIES_DIR.glob("*.txt"))
    
    total_diaries = len(entries)
    total_words = 0
    total_chars = 0
    
    for entry in entries:
        with open(entry, 'r', encoding='utf-8') as f:
            content = f.read()
            # 移除时间戳和标签行
            lines = content.split('\n')
            if lines and lines[0].startswith("[") and "]" in lines[0]:
                lines = lines[1:]
            if lines and lines[0].startswith("Tags: "):
                lines = lines[1:]
            content = '\n'.join(lines)
            
            total_chars += len(content)
            total_words += len(content.split())
    
    return {
        'total_diaries': total_diaries,
        'total_words': total_words,
        'total_chars': total_chars,
        'entries': entries
    }

def get_tag_stats():
    """获取标签使用统计"""
    from .storage import get_tags
    
    tag_data = get_tags()
    stats = []
    
    for tag, dates in tag_data.items():
        stats.append({
            'tag': tag,
            'count': len(dates),
            'dates': sorted(dates, reverse=True)
        })
    
    # 按使用频率排序
    stats.sort(key=lambda x: x['count'], reverse=True)
    return stats

def parse_relative_date(relative_str):
    """解析相对日期字符串"""
    today = datetime.now().date()
    
    relative_map = {
        '今天': 0,
        '昨天': 1,
        '前天': 2,
        '上周': 7,
        '上周': 7,
        '上个月': 30,
        '上个月': 30,
    }
    
    if relative_str in relative_map:
        days = relative_map[relative_str]
        return (today - timedelta(days=days)).strftime("%Y-%m-%d")
    
    # 处理 "N天前" 格式
    if relative_str.endswith('天前'):
        try:
            days = int(relative_str[:-2])
            return (today - timedelta(days=days)).strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    return None

def export_diary(date_str, export_path=None):
    """导出一篇日记为独立文件"""
    file_path = ENTRIES_DIR / f"{date_str}.txt"
    if not file_path.exists():
        return None
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if export_path is None:
        export_path = f"diary_{date_str}.md"
    
    with open(export_path, 'w', encoding='utf-8') as f:
        f.write(f"# {date_str} 的日记\n\n")
        f.write(content)
    
    return export_path

def export_all_diaries(export_dir="exports"):
    """导出所有日记到指定目录"""
    export_path = Path(export_dir)
    export_path.mkdir(exist_ok=True)
    
    entries = sorted(ENTRIES_DIR.glob("*.txt"), reverse=True)
    exported = []
    
    for entry in entries:
        date_str = entry.stem
        with open(entry, 'r', encoding='utf-8') as f:
            content = f.read()
        
        export_file = export_path / f"{date_str}.md"
        with open(export_file, 'w', encoding='utf-8') as f:
            f.write(f"# {date_str} 的日记\n\n")
            f.write(content)
        exported.append(date_str)
    
    return exported, export_path
