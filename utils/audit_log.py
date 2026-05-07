import os
import json
from datetime import datetime
from pathlib import Path
from threading import Lock

AUDIT_LOG_FILE = Path("data") / "audit.log"
AUDIT_LOG_FILE.parent.mkdir(exist_ok=True)

_lock = Lock()

def log_action(user_id, username, action, details=None, ip_address=None):
    """记录操作日志"""
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'user_id': user_id,
        'username': username,
        'action': action,
        'details': details or {},
        'ip_address': ip_address
    }
    
    with _lock:
        with open(AUDIT_LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')

def get_audit_logs(limit=100, user_id=None):
    """获取操作日志"""
    logs = []
    if AUDIT_LOG_FILE.exists():
        with open(AUDIT_LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entry = json.loads(line)
                        if user_id is None or entry.get('user_id') == user_id:
                            logs.append(entry)
                    except json.JSONDecodeError:
                        continue
    
    return sorted(logs, key=lambda x: x['timestamp'], reverse=True)[:limit]

def log_login(username, ip_address=None, success=True):
    """记录登录操作"""
    log_action(None, username, 'login', {'success': success}, ip_address)

def log_logout(user_id, username, ip_address=None):
    """记录登出操作"""
    log_action(user_id, username, 'logout', {}, ip_address)

def log_create_user(admin_id, admin_name, new_username, role):
    """记录创建用户"""
    log_action(admin_id, admin_name, 'create_user', {
        'new_username': new_username,
        'role': role
    })

def log_delete_user(admin_id, admin_name, deleted_username):
    """记录删除用户"""
    log_action(admin_id, admin_name, 'delete_user', {
        'deleted_username': deleted_username
    })

def log_update_user_role(admin_id, admin_name, username, new_role):
    """记录更新用户角色"""
    log_action(admin_id, admin_name, 'update_user_role', {
        'username': username,
        'new_role': new_role
    })

def log_reset_password(admin_id, admin_name, username):
    """记录重置密码"""
    log_action(admin_id, admin_name, 'reset_password', {
        'username': username
    })

def log_create_entry(user_id, username, date_str):
    """记录创建日记"""
    log_action(user_id, username, 'create_entry', {'date': date_str})

def log_update_entry(user_id, username, date_str):
    """记录更新日记"""
    log_action(user_id, username, 'update_entry', {'date': date_str})

def log_delete_entry(user_id, username, date_str):
    """记录删除日记"""
    log_action(user_id, username, 'delete_entry', {'date': date_str})

def log_export_data(user_id, username, export_format):
    """记录导出数据"""
    log_action(user_id, username, 'export_data', {'format': export_format})

def log_import_data(user_id, username, count):
    """记录导入数据"""
    log_action(user_id, username, 'import_data', {'count': count})

def log_change_password(user_id, username):
    """记录修改密码"""
    log_action(user_id, username, 'change_password', {})

def log_change_settings(user_id, username, settings_changed):
    """记录修改设置"""
    log_action(user_id, username, 'change_settings', {'changed': settings_changed})