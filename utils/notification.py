"""
通知系统模块

提供多模式通知功能，支持终端、PyQt 和 Web 端
"""

import sys
import json
from datetime import datetime
from pathlib import Path

# 通知级别
NOTIFICATION_LEVELS = {
    'info': 'INFO',
    'warning': 'WARNING',
    'error': 'ERROR',
    'success': 'SUCCESS'
}

# Web端通知数据文件
NOTIFICATIONS_FILE = Path("notifications.json")

def init_notifications_file():
    """初始化通知数据文件"""
    if not NOTIFICATIONS_FILE.exists():
        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)

def get_notifications(limit=50, unread_only=False):
    """获取通知列表

    Args:
        limit: 返回的最大通知数量
        unread_only: 是否只返回未读通知

    Returns:
        list: 通知列表
    """
    init_notifications_file()

    with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
        notifications = json.load(f)

    if unread_only:
        notifications = [n for n in notifications if not n.get('read', False)]

    return notifications[:limit]

def add_notification(message, level='info', title=''):
    """添加新通知

    Args:
        message: 通知消息内容
        level: 通知级别 (info, warning, error, success)
        title: 通知标题

    Returns:
        dict: 创建的通知对象
    """
    init_notifications_file()

    with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
        notifications = json.load(f)

    notification = {
        'id': datetime.now().strftime('%Y%m%d%H%M%S%f'),
        'title': title,
        'message': message,
        'level': level,
        'read': False,
        'created_at': datetime.now().isoformat()
    }

    notifications.insert(0, notification)

    with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(notifications, f, ensure_ascii=False, indent=2)

    return notification

def mark_as_read(notification_id):
    """标记通知为已读

    Args:
        notification_id: 通知ID

    Returns:
        bool: 是否成功标记
    """
    init_notifications_file()

    with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
        notifications = json.load(f)

    for notification in notifications:
        if notification['id'] == notification_id:
            notification['read'] = True
            with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
                json.dump(notifications, f, ensure_ascii=False, indent=2)
            return True

    return False

def mark_all_as_read():
    """标记所有通知为已读"""
    init_notifications_file()

    with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
        notifications = json.load(f)

    for notification in notifications:
        notification['read'] = True

    with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(notifications, f, ensure_ascii=False, indent=2)

def delete_notification(notification_id):
    """删除通知

    Args:
        notification_id: 通知ID

    Returns:
        bool: 是否成功删除
    """
    init_notifications_file()

    with open(NOTIFICATIONS_FILE, 'r', encoding='utf-8') as f:
        notifications = json.load(f)

    original_len = len(notifications)
    notifications = [n for n in notifications if n['id'] != notification_id]

    if len(notifications) < original_len:
        with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(notifications, f, ensure_ascii=False, indent=2)
        return True

    return False

def get_unread_count():
    """获取未读通知数量

    Returns:
        int: 未读通知数量
    """
    notifications = get_notifications(unread_only=True)
    return len(notifications)

def clear_all_notifications():
    """清空所有通知"""
    with open(NOTIFICATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False, indent=2)

def format_notification(message, level='info'):
    """格式化通知消息"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    level_str = NOTIFICATION_LEVELS.get(level, 'INFO')
    return f"[{timestamp}] [{level_str}] {message}"

def show_notification(message, level='info', mode='terminal'):
    """显示通知
    
    Args:
        message: 通知消息
        level: 通知级别 (info, warning, error, success)
        mode: 显示模式 (terminal, pyqt, web)
    """
    from utils.config import get_config
    
    config = get_config()
    if not config.get('notifications', {}).get('enabled', True):
        return
    
    # 检查通知级别
    notification_level = config.get('notifications', {}).get('level', 'info')
    if level == 'info' and notification_level != 'info':
        return
    if level == 'warning' and notification_level == 'error':
        return
    
    if mode == 'terminal':
        _show_terminal_notification(message, level)
    elif mode == 'pyqt':
        _show_pyqt_notification(message, level)
    elif mode == 'web':
        _show_web_notification(message, level)

def _show_terminal_notification(message, level='info'):
    """在终端中显示通知"""
    from colorama import Fore, Style
    
    color_map = {
        'info': Fore.BLUE,
        'warning': Fore.YELLOW,
        'error': Fore.RED,
        'success': Fore.GREEN
    }
    
    color = color_map.get(level, Fore.WHITE)
    formatted_message = format_notification(message, level)
    print(f"{color}{formatted_message}{Style.RESET_ALL}")

def _show_pyqt_notification(message, level='info'):
    """在 PyQt 中显示通知"""
    try:
        from PyQt6.QtWidgets import QMessageBox
        from PyQt6.QtCore import Qt
        
        icon_map = {
            'info': QMessageBox.Icon.Information,
            'warning': QMessageBox.Icon.Warning,
            'error': QMessageBox.Icon.Critical,
            'success': QMessageBox.Icon.Information
        }
        
        icon = icon_map.get(level, QMessageBox.Icon.Information)
        title_map = {
            'info': '信息',
            'warning': '警告',
            'error': '错误',
            'success': '成功'
        }
        title = title_map.get(level, '信息')
        
        msg_box = QMessageBox()
        msg_box.setIcon(icon)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()
    except ImportError:
        # 回退到终端通知
        _show_terminal_notification(message, level)

def _show_web_notification(message, level='info'):
    """在 Web 中显示通知"""
    # Web 端的通知由 Flask 处理
    pass

def log_notification(message, level='info'):
    """记录通知到日志"""
    from utils.logger import log_action, log_error, log_warning
    
    if level == 'error':
        log_error(message)
    elif level == 'warning':
        log_warning(message)
    else:
        log_action(message)
