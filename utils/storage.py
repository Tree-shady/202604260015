from datetime import datetime
from pathlib import Path
from .config import DATE_FORMAT, IMAGES_DIR
from .models import get_session, Entry, Tag, Image

# 标签数据缓存
_tags_cache = None

# 日记内容缓存（按日期）
_entry_cache = {}

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
        session = get_session()
        entry = session.query(Entry).filter_by(date_str=date_str).first()
        if not entry:
            return "", [], ""
        
        timestamp = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        tags = [tag.name for tag in entry.tags]
        content = entry.content
        
        _entry_cache[date_str] = (timestamp, tags, content)
    
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
    """获取所有日记"""
    session = get_session()
    entries = session.query(Entry).order_by(Entry.date_str.desc()).all()
    # 返回模拟的文件路径对象，保持向后兼容
    class MockPath:
        def __init__(self, date_str):
            self.stem = date_str
    return [MockPath(entry.date_str) for entry in entries]

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
