"""
通知系统模块

提供多模式通知功能，支持终端、PyQt 和 Web 端
"""

import sys
from datetime import datetime
from .models import get_session, Notification

# 通知级别
NOTIFICATION_LEVELS = {
    'info': 'INFO',
    'warning': 'WARNING',
    'error': 'ERROR',
    'success': 'SUCCESS'
}

def get_notifications(limit=50, unread_only=False):
    """获取通知列表

    Args:
        limit: 返回的最大通知数量
        unread_only: 是否只返回未读通知

    Returns:
        list: 通知列表
    """
    db_session = get_session()
    query = db_session.query(Notification).order_by(Notification.created_at.desc())
    
    if unread_only:
        query = query.filter_by(read=False)
    
    notifications = query.limit(limit).all()
    
    return [{
        'id': str(notification.id),
        'title': notification.title,
        'message': notification.message,
        'level': notification.level,
        'read': notification.read,
        'created_at': notification.created_at.isoformat()
    } for notification in notifications]

def add_notification(message, level='info', title=''):
    """添加新通知

    Args:
        message: 通知消息内容
        level: 通知级别 (info, warning, error, success)
        title: 通知标题

    Returns:
        dict: 创建的通知对象
    """
    db_session = get_session()
    
    notification = Notification(
        title=title,
        message=message,
        level=level,
        read=False
    )
    
    db_session.add(notification)
    db_session.commit()
    
    return {
        'id': str(notification.id),
        'title': notification.title,
        'message': notification.message,
        'level': notification.level,
        'read': notification.read,
        'created_at': notification.created_at.isoformat()
    }

def mark_as_read(notification_id):
    """标记通知为已读

    Args:
        notification_id: 通知ID

    Returns:
        bool: 是否成功标记
    """
    db_session = get_session()
    try:
        notification = db_session.query(Notification).filter_by(id=int(notification_id)).first()
        if notification:
            notification.read = True
            db_session.commit()
            return True
    except ValueError:
        pass
    return False

def mark_all_as_read():
    """标记所有通知为已读"""
    db_session = get_session()
    db_session.query(Notification).filter_by(read=False).update({'read': True})
    db_session.commit()

def delete_notification(notification_id):
    """删除通知

    Args:
        notification_id: 通知ID

    Returns:
        bool: 是否成功删除
    """
    db_session = get_session()
    try:
        notification = db_session.query(Notification).filter_by(id=int(notification_id)).first()
        if notification:
            db_session.delete(notification)
            db_session.commit()
            return True
    except ValueError:
        pass
    return False

def get_unread_count():
    """获取未读通知数量

    Returns:
        int: 未读通知数量
    """
    db_session = get_session()
    return db_session.query(Notification).filter_by(read=False).count()

def clear_all_notifications():
    """清空所有通知"""
    db_session = get_session()
    db_session.query(Notification).delete()
    db_session.commit()

def create_system_notification(message, level='info'):
    """创建系统通知（管理员使用）
    
    Args:
        message: 通知消息内容
        level: 通知级别
    """
    return add_notification(message, level, title='系统通知')

# 兼容旧函数名
def init_notifications_file():
    """初始化通知数据文件（兼容旧函数）"""
    pass

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
