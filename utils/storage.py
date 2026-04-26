import json
from datetime import datetime
from pathlib import Path
from .config import ENTRIES_DIR, DATE_FORMAT, TAGS_FILE, MOODS_FILE, IMAGES_DIR

# 标签数据缓存
_tags_cache = None

# 日记内容缓存（按日期）
_entry_cache = {}

def ensure_dir():
    """确保日记存放目录存在"""
    ENTRIES_DIR.mkdir(exist_ok=True)
    IMAGES_DIR.mkdir(exist_ok=True)
    # 初始化标签文件
    if not TAGS_FILE.exists():
        with open(TAGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    # 初始化心情数据文件
    if not MOODS_FILE.exists():
        with open(MOODS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

def get_today_str():
    """获取今天的日期字符串"""
    return datetime.now().strftime(DATE_FORMAT)

def get_file_path(date_str):
    """根据日期字符串获取文件路径"""
    return ENTRIES_DIR / f"{date_str}.txt"

def get_tags():
    """获取标签数据（带缓存）"""
    global _tags_cache
    if _tags_cache is None:
        with open(TAGS_FILE, 'r', encoding='utf-8') as f:
            _tags_cache = json.load(f)
    return _tags_cache

def save_tags(tags):
    """保存标签数据（清除缓存）"""
    global _tags_cache
    with open(TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)
    _tags_cache = tags  # 更新缓存

def update_tags_index(date_str, tags):
    """更新标签索引（使用缓存）
    
    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
        tags: 标签列表
    """
    tag_data = get_tags().copy()
    
    # 移除旧标签关联
    for tag, dates in list(tag_data.items()):  # 使用 list() 避免遍历中修改
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

def get_entry_content(date_str):
    """获取日记内容（带缓存）
    
    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
    
    Returns:
        tuple: (timestamp, tags, content)
            timestamp: 时间戳字符串
            tags: 标签列表
            content: 日记内容
    """
    global _entry_cache
    if date_str not in _entry_cache:
        file_path = get_file_path(date_str)
        if not file_path.exists():
            return "", [], ""
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 解析内容
        lines = content.split('\n')
        timestamp = ""
        tags = []
        entry_content = ""
        
        if lines and lines[0].startswith("[") and "]" in lines[0]:
            timestamp = lines[0][1:-1]
            lines = lines[1:]
        
        if lines and lines[0].startswith("Tags: "):
            tags_str = lines[0][6:]
            tags = [tag.strip() for tag in tags_str.split(',')]
            lines = lines[1:]
        
        entry_content = '\n'.join(lines)
        _entry_cache[date_str] = (timestamp, tags, entry_content)
    
    return _entry_cache[date_str]

def clear_entry_cache(date_str=None):
    """清除日记内容缓存"""
    global _entry_cache
    if date_str:
        if date_str in _entry_cache:
            del _entry_cache[date_str]
    else:
        _entry_cache.clear()

def get_entries():
    """获取所有日记文件"""
    return sorted(ENTRIES_DIR.glob("*.txt"), reverse=True)

# 图片处理相关函数
def upload_image(image_file, date_str):
    """上传图片并返回相对路径
    
    Args:
        image_file: 图片文件对象
        date_str: 日期字符串，格式 YYYY-MM-DD
    
    Returns:
        str: 图片的相对路径
    """
    # 创建日期目录
    date_dir = IMAGES_DIR / date_str
    date_dir.mkdir(exist_ok=True)
    
    # 生成唯一文件名
    timestamp = datetime.now().strftime("%H%M%S")
    filename = f"{timestamp}_{image_file.filename}"
    filepath = date_dir / filename
    
    # 保存图片
    with open(filepath, 'wb') as f:
        f.write(image_file.read())
    
    # 返回相对路径
    return f"images/{date_str}/{filename}"

def get_image_path(image_rel_path):
    """获取图片的绝对路径
    
    Args:
        image_rel_path: 图片的相对路径
    
    Returns:
        Path: 图片的绝对路径
    """
    return Path(image_rel_path)

def list_images(date_str):
    """列出指定日期的所有图片
    
    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
    
    Returns:
        list: 图片路径列表
    """
    date_dir = IMAGES_DIR / date_str
    if not date_dir.exists():
        return []
    
    images = []
    for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']:
        images.extend(date_dir.glob(f"*{ext}"))
    
    return images

def delete_image(image_rel_path):
    """删除图片
    
    Args:
        image_rel_path: 图片的相对路径
    
    Returns:
        bool: 是否删除成功
    """
    try:
        image_path = get_image_path(image_rel_path)
        if image_path.exists():
            image_path.unlink()
            return True
        return False
    except Exception:
        return False
