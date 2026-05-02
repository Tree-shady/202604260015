import re
import html
from datetime import datetime
from .config import DATE_FORMAT

def validate_date_str(date_str):
    """验证日期字符串，防止路径遍历攻击"""
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
    try:
        datetime.strptime(date_str, DATE_FORMAT)
        return True
    except ValueError:
        return False

def validate_tag(tag):
    """验证标签名称，防止恶意输入"""
    if not re.match(r'^[\w\u4e00-\u9fa5-]+$', tag):
        return False
    if len(tag) > 50:
        return False
    return True

def sanitize_tag(tag):
    """对标签进行 XSS 防护转义"""
    return html.escape(tag.strip())

def sanitize_tags(tags_str):
    """对多个标签进行 XSS 防护转义"""
    if not tags_str:
        return []
    tags = [tag.strip() for tag in tags_str.split(',')]
    return [sanitize_tag(tag) for tag in tags if tag]

def validate_relative_date(date_str):
    """验证相对日期字符串（如今天、昨天等）"""
    relative_dates = {
        '今天': 0,
        '昨天': 1,
        '前天': 2,
        '明天': -1,
        '后天': -2
    }
    for key, offset in relative_dates.items():
        if key in date_str:
            return offset
    return None
