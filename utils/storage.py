from datetime import datetime
from pathlib import Path
from collections import OrderedDict
from .config import DATE_FORMAT, IMAGES_DIR
from .models import get_session, Entry, Tag, Image

# 标签数据缓存
_tags_cache = None

# 日记内容缓存（按日期）- 使用有序字典实现LRU缓存
MAX_CACHE_SIZE = 100
_entry_cache = OrderedDict()

# 日记列表缓存
_entries_list_cache = {}

def _get_cached_entry(cache_key):
    """获取缓存的日记内容，实现LRU机制"""
    global _entry_cache
    if cache_key in _entry_cache:
        # 将访问的项移到末尾（最近使用）
        _entry_cache.move_to_end(cache_key)
        return _entry_cache[cache_key]
    return None

def _set_cached_entry(cache_key, value):
    """设置日记内容缓存，实现LRU机制"""
    global _entry_cache
    _entry_cache[cache_key] = value
    _entry_cache.move_to_end(cache_key)
    # 如果缓存超过最大大小，删除最旧的项
    while len(_entry_cache) > MAX_CACHE_SIZE:
        _entry_cache.popitem(last=False)

def ensure_dir():
    """确保必要的目录存在"""
    IMAGES_DIR.mkdir(exist_ok=True)

def get_today_str():
    """获取今天的日期字符串"""
    return datetime.now().strftime(DATE_FORMAT)

def get_file_path(date_str):
    """根据日期字符串获取文件路径（保持向后兼容）"""
    # 由于现在使用数据库存储，此函数仅用于保持向后兼容
    from .config import ENTRIES_DIR
    return ENTRIES_DIR / f"{date_str}.txt"

def get_tags():
    """获取标签数据（带缓存）"""
    global _tags_cache
    if _tags_cache is None:
        session = get_session()
        tags = session.query(Tag).all()
        _tags_cache = {tag.name: [entry.date_str for entry in tag.entries] for tag in tags}
    return _tags_cache

def save_tags(tags):
    """保存标签数据（清除缓存）"""
    global _tags_cache
    _tags_cache = tags  # 更新缓存

def update_tags_index(date_str, tags):
    """更新标签索引
    
    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
        tags: 标签列表
    """
    session = get_session()
    
    # 查找对应日记
    entry = session.query(Entry).filter_by(date_str=date_str).first()
    if not entry:
        return
    
    # 清除旧标签关联
    entry.tags = []
    
    # 添加新标签关联
    for tag_name in tags:
        if tag_name:
            # 查找或创建标签
            tag = session.query(Tag).filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                session.add(tag)
            entry.tags.append(tag)
    
    session.commit()
    clear_entry_cache(date_str)
    global _tags_cache
    _tags_cache = None  # 清除标签缓存

def get_entry_content(date_str, user_id=1):
    """获取日记内容（带缓存）

    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
        user_id: 用户ID

    Returns:
        tuple: (timestamp, tags, content)
            timestamp: 时间戳字符串
            tags: 标签列表
            content: 日记内容
    """
    cache_key = f"{date_str}_{user_id}"
    cached = _get_cached_entry(cache_key)
    if cached:
        return cached
    
    session = get_session()
    entry = session.query(Entry).filter_by(date_str=date_str, user_id=user_id).first()
    if entry:
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        tags = [tag.name for tag in entry.tags]
        content = entry.content
        _set_cached_entry(cache_key, (timestamp, tags, content))
        return (timestamp, tags, content)
    else:
        file_path = get_file_path(date_str)
        if file_path.exists():
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
                timestamp = ""
                tags = []
                if lines and lines[0].startswith("[") and "]" in lines[0]:
                    timestamp = lines[0][1:-1]
                    lines = lines[1:]
                if lines and lines[0].startswith("Tags: "):
                    tags = [t.strip() for t in lines[0][6:].split(",") if t.strip()]
                    lines = lines[1:]
                content = '\n'.join(lines)
                _entry_cache[cache_key] = (timestamp, tags, content)
        else:
            _entry_cache[cache_key] = ("", [], "")

    return _entry_cache[cache_key]

def clear_entry_cache(date_str=None, user_id=None):
    """清除日记内容缓存"""
    global _entry_cache
    if date_str and user_id:
        cache_key = f"{date_str}_{user_id}"
        if cache_key in _entry_cache:
            del _entry_cache[cache_key]
    elif date_str:
        # 删除所有用户的该日期缓存
        keys_to_delete = [k for k in _entry_cache if k.startswith(f"{date_str}_")]
        for k in keys_to_delete:
            del _entry_cache[k]
    else:
        _entry_cache.clear()
    # 清除日记列表缓存
    global _entries_list_cache
    if user_id:
        if user_id in _entries_list_cache:
            del _entries_list_cache[user_id]
    else:
        _entries_list_cache.clear()

def get_entries(user_id=1):
    """获取所有日记（带缓存）"""
    global _entries_list_cache
    if user_id in _entries_list_cache:
        return _entries_list_cache[user_id]
    
    session = get_session()
    entries = session.query(Entry).filter_by(user_id=user_id).order_by(Entry.date_str.desc()).all()
    class MockPath:
        def __init__(self, date_str):
            self.stem = date_str
    result = [MockPath(entry.date_str) for entry in entries]
    _entries_list_cache[user_id] = result
    return result

def save_entry(date_str, content, tags=None, user_id=1):
    """保存日记（通过数据库）

    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
        content: 日记内容
        tags: 标签列表
        user_id: 用户ID

    Returns:
        Entry: 保存的日记对象
    """
    session = get_session()

    entry = session.query(Entry).filter_by(date_str=date_str, user_id=user_id).first()
    if entry:
        entry.content = content
        entry.timestamp = datetime.now()
    else:
        entry = Entry(
            user_id=user_id,
            date_str=date_str,
            content=content,
            timestamp=datetime.now()
        )
        session.add(entry)
        session.flush()

    if tags is not None:
        entry.tags = []
        for tag_name in tags:
            if tag_name:
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                entry.tags.append(tag)

    session.commit()
    clear_entry_cache(date_str)
    global _tags_cache
    _tags_cache = None

    return entry

def delete_entry(date_str, user_id=1):
    """删除日记（通过数据库）

    Args:
        date_str: 日期字符串，格式 YYYY-MM-DD
        user_id: 用户ID

    Returns:
        bool: 是否删除成功
    """
    session = get_session()
    entry = session.query(Entry).filter_by(date_str=date_str, user_id=user_id).first()
    if entry:
        session.delete(entry)
        session.commit()
        clear_entry_cache(date_str)
        global _tags_cache
        _tags_cache = None
        return True
    return False

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
    
    # 保存到数据库
    session = get_session()
    entry = session.query(Entry).filter_by(date_str=date_str).first()
    if entry:
        image = Image(
            entry_id=entry.id,
            file_path=str(filepath),
            filename=filename
        )
        session.add(image)
        session.commit()
    
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
    session = get_session()
    entry = session.query(Entry).filter_by(date_str=date_str).first()
    if not entry:
        return []
    
    # 从数据库获取图片
    images = []
    for image in entry.images:
        images.append(Path(image.file_path))
    
    # 同时检查文件系统，保持向后兼容
    date_dir = IMAGES_DIR / date_str
    if date_dir.exists():
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
        
        # 从数据库删除
        session = get_session()
        image = session.query(Image).filter_by(file_path=str(image_path)).first()
        if image:
            session.delete(image)
            session.commit()
        
        return True
    except Exception:
        return False
