"""
设置管理模块

提供系统设置的管理功能
"""

from utils.config import get_config, save_config, DEFAULT_CONFIG
from utils.notification import show_notification

def show_settings():
    """显示设置菜单"""
    from colorama import Fore, Style
    
    config = get_config()
    
    while True:
        print(f"\n{Fore.CYAN}{'=' * 40}")
        print(f"{Fore.GREEN}{Style.BRIGHT}        系统设置")
        print(f"{Fore.CYAN}{'=' * 40}")
        print(f"{Fore.WHITE}1. 主题设置: {config.get('theme', 'light')}")
        print(f"{Fore.WHITE}2. 日期格式: {config.get('date_format', '%Y-%m-%d')}")
        print(f"{Fore.WHITE}3. 自动备份: {'开启' if config.get('backup_enabled', True) else '关闭'}")
        print(f"{Fore.WHITE}4. 自动保存: {'开启' if config.get('auto_save', True) else '关闭'}")
        print(f"{Fore.WHITE}5. 通知设置: {'开启' if config.get('notifications', {}).get('enabled', True) else '关闭'}")
        print(f"{Fore.WHITE}6. 重置所有设置")
        print(f"{Fore.RED}0. 返回主菜单")
        print(f"{Fore.CYAN}{'=' * 40}")
        
        choice = input("请选择操作: ").strip()
        
        if choice == '1':
            _set_theme()
        elif choice == '2':
            _set_date_format()
        elif choice == '3':
            _toggle_backup()
        elif choice == '4':
            _toggle_auto_save()
        elif choice == '5':
            _toggle_notifications()
        elif choice == '6':
            _reset_settings()
        elif choice == '0':
            break
        else:
            print(f"{Fore.RED}无效选择，请重新输入")

def _set_theme():
    """设置主题"""
    from colorama import Fore
    
    print(f"\n{Fore.WHITE}请选择主题:")
    print(f"{Fore.WHITE}1. 浅色 (light)")
    print(f"{Fore.WHITE}2. 深色 (dark)")
    
    choice = input("请选择: ").strip()
    
    if choice == '1':
        config = get_config()
        config['theme'] = 'light'
        save_config(config)
        show_notification("主题已设置为浅色", 'success')
    elif choice == '2':
        config = get_config()
        config['theme'] = 'dark'
        save_config(config)
        show_notification("主题已设置为深色", 'success')
    else:
        show_notification("无效选择", 'error')

def _set_date_format():
    """设置日期格式"""
    from colorama import Fore
    from datetime import datetime
    
    print(f"\n{Fore.WHITE}当前日期格式: {get_config().get('date_format', '%Y-%m-%d')}")
    print(f"{Fore.WHITE}示例: %Y-%m-%d (2026-04-26)")
    print(f"{Fore.WHITE}       %d/%m/%Y (26/04/2026)")
    
    new_format = input("请输入新的日期格式: ").strip()
    
    if new_format:
        try:
            # 测试格式是否有效
            datetime.now().strftime(new_format)
            config = get_config()
            config['date_format'] = new_format
            save_config(config)
            show_notification("日期格式已更新", 'success')
        except ValueError:
            show_notification("无效的日期格式", 'error')

def _toggle_backup():
    """切换自动备份"""
    config = get_config()
    current = config.get('backup_enabled', True)
    config['backup_enabled'] = not current
    save_config(config)
    status = "开启" if not current else "关闭"
    show_notification(f"自动备份已{status}", 'success')

def _toggle_auto_save():
    """切换自动保存"""
    config = get_config()
    current = config.get('auto_save', True)
    config['auto_save'] = not current
    save_config(config)
    status = "开启" if not current else "关闭"
    show_notification(f"自动保存已{status}", 'success')

def _toggle_notifications():
    """切换通知"""
    config = get_config()
    notifications = config.get('notifications', {})
    current = notifications.get('enabled', True)
    notifications['enabled'] = not current
    config['notifications'] = notifications
    save_config(config)
    status = "开启" if not current else "关闭"
    show_notification(f"通知已{status}", 'success')

def _reset_settings():
    """重置所有设置"""
    from colorama import Fore
    
    confirm = input(f"{Fore.RED}确认重置所有设置到默认值吗？(y/n): ").strip()
    if confirm.lower() == 'y':
        from utils.config import reset_config
        reset_config()
        show_notification("所有设置已重置为默认值", 'success')
    else:
        show_notification("已取消重置", 'info')
