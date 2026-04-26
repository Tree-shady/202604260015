"""
通知系统模块

提供多模式通知功能，支持终端、PyQt 和 Web 端
"""

import sys
from datetime import datetime

# 通知级别
NOTIFICATION_LEVELS = {
    'info': 'INFO',
    'warning': 'WARNING',
    'error': 'ERROR',
    'success': 'SUCCESS'
}

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
