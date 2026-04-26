import json
from datetime import datetime
from pathlib import Path
from .config import ENTRIES_DIR, DATE_FORMAT, TAGS_FILE

def ensure_dir():
    """确保日记存放目录存在"""
    ENTRIES_DIR.mkdir(exist_ok=True)
    # 初始化标签文件
    if not TAGS_FILE.exists():
        with open(TAGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

def get_today_str():
    """获取今天的日期字符串"""
    return datetime.now().strftime(DATE_FORMAT)

def get_file_path(date_str):
    """根据日期字符串获取文件路径"""
    return ENTRIES_DIR / f"{date_str}.txt"

def get_tags():
    """获取标签数据"""
    with open(TAGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_tags(tags):
    """保存标签数据"""
    with open(TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

def update_tags_index(date_str, tags):
    """更新标签索引"""
    tag_data = get_tags()
    
    # 移除旧标签关联
    for tag, dates in tag_data.items():
        if date_str in dates:
            dates.remove(date_str)
            if not dates:
                del tag_data[tag]
    
    # 添加新标签关联
    for tag in tags:
        if tag not in tag_data:
            tag_data[tag] = []
        if date_str not in tag_data[tag]:
            tag_data[tag].append(date_str)
    
    save_tags(tag_data)
