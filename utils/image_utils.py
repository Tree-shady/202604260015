"""
图片处理工具模块
"""
from pathlib import Path
from typing import Optional, Tuple
import uuid

# 图片魔法字节验证
IMAGE_MAGIC = {
    'jpeg': [b'\xff\xd8\xff'],
    'png': [b'\x89PNG'],
    'gif': [b'GIF87a', b'GIF89a'],
    'webp': [b'RIFF'],
}

# 允许的图片扩展名
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
# 图片大小限制（5MB）
MAX_IMAGE_SIZE = 5 * 1024 * 1024


def validate_image_magic(filepath: Path) -> Optional[str]:
    """
    验证图片文件的魔法字节

    Args:
        filepath: 图片文件路径

    Returns:
        图片类型或 None
    """
    try:
        with open(filepath, 'rb') as f:
            header = f.read(16)
        
        for img_type, magics in IMAGE_MAGIC.items():
            for magic in magics:
                if header.startswith(magic):
                    if img_type == 'jpeg':
                        return 'jpeg'
                    elif img_type == 'png':
                        return 'png'
                    elif img_type == 'gif':
                        return 'gif'
                    elif img_type == 'webp':
                        if b'WEBP' in header[:12]:
                            return 'webp'
        return None
    except Exception:
        return None


def allowed_file(filename: str) -> bool:
    """
    检查文件扩展名是否允许

    Args:
        filename: 文件名

    Returns:
        是否允许
    """
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def generate_unique_filename(original_filename: str) -> str:
    """
    生成唯一文件名

    Args:
        original_filename: 原始文件名

    Returns:
        唯一文件名
    """
    ext = original_filename.rsplit('.', 1)[1].lower() if '.' in original_filename else 'jpg'
    return f"{uuid.uuid4().hex}.{ext}"


def validate_image_file(file) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    完整验证上传的图片文件

    Args:
        file: Flask 文件对象

    Returns:
        (是否有效, 错误信息, 文件类型)
    """
    # 检查文件大小
    if len(file.read()) > MAX_IMAGE_SIZE:
        file.seek(0)
        return False, "图片大小不能超过 5MB", None
    
    file.seek(0)
    
    # 检查文件扩展名
    if not allowed_file(file.filename):
        return False, "只允许上传 JPG、PNG、GIF 或 WEBP 格式的图片", None
    
    return True, None, None
