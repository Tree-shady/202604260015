"""
用户认证模块

提供用户注册、登录、权限验证等功能
"""

import hashlib
import secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, flash
from .models import get_session, User

SALT_LENGTH = 32

USER_ROLES = {
    'superadmin': '超级管理员',
    'admin': '管理员',
    'user': '普通用户'
}

def get_admin_password():
    """获取管理员密码（优先使用环境变量，否则生成随机密码）"""
    import os
    admin_password = os.environ.get('ADMIN_PASSWORD')
    if admin_password:
        return admin_password
    generated_password = secrets.token_urlsafe(12)
    print(f"\n{'=' * 60}")
    print(f"  首次启动 - 已生成随机管理员密码")
    print(f"  用户名: Administrator")
    print(f"  密码: {generated_password}")
    print(f"  请尽快修改密码！")
    print(f"{'=' * 60}\n")
    return generated_password

def init_users():
    """初始化用户数据"""
    session = get_session()
    admin_user = session.query(User).filter_by(username='Administrator').first()
    if not admin_user:
        admin_user = User(
            username='Administrator',
            password_hash=hash_password(get_admin_password()),
            role='admin',
            active=True
        )
        session.add(admin_user)
        session.commit()

def hash_password(password, salt=None):
    """哈希密码

    Args:
        password: 明文密码
        salt: 盐值，如果为None则生成随机盐

    Returns:
        str: 哈希后的密码（格式：salt$hash）
    """
    if salt is None:
        salt = secrets.token_hex(SALT_LENGTH)

    hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    hash_hex = hash_obj.hex()
    return f"{salt}${hash_hex}"

def verify_password(password, stored_password):
    """验证密码

    Args:
        password: 待验证的明文密码
        stored_password: 存储的哈希密码（格式：salt$hash）

    Returns:
        bool: 密码是否正确
    """
    try:
        salt, stored_hash = stored_password.split('$')
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
        return hash_obj.hex() == stored_hash
    except Exception:
        return False

def get_users():
    """获取所有用户列表

    Returns:
        list: 用户列表
    """
    session = get_session()
    users = session.query(User).all()
    user_list = []
    
    for user in users:
        # 检查账号是否过期
        if user.expires_at and user.expires_at < datetime.now() and user.active:
            user.active = False
            session.commit()
        
        # 检查密码是否过期
        password_expired = False
        if user.password_expires_at and user.password_expires_at < datetime.now():
            password_expired = True
        
        user_list.append({
            'id': user.id,
            'username': user.username,
            'password_hash': user.password_hash,
            'role': user.role,
            'created_at': user.created_at.isoformat(),
            'last_login': user.updated_at.isoformat() if user.updated_at else None,
            'is_active': user.active,
            'expires_at': user.expires_at.isoformat() if user.expires_at else None,
            'is_temporary': user.is_temporary,
            'password_expired': password_expired,
            'password_expires_at': user.password_expires_at.isoformat() if user.password_expires_at else None
        })
    
    return user_list

def get_user_by_username(username):
    """根据用户名获取用户

    Args:
        username: 用户名

    Returns:
        dict: 用户信息，如果不存在返回None
    """
    session = get_session()
    user = session.query(User).filter_by(username=username).first()
    if user:
        # 检查账号是否过期
        if user.expires_at and user.expires_at < datetime.now() and user.active:
            user.active = False
            session.commit()
        
        # 检查密码是否过期
        password_expired = False
        if user.password_expires_at and user.password_expires_at < datetime.now():
            password_expired = True
        
        return {
            'id': user.id,
            'username': user.username,
            'password_hash': user.password_hash,
            'role': user.role,
            'created_at': user.created_at.isoformat(),
            'last_login': user.updated_at.isoformat() if user.updated_at else None,
            'is_active': user.active,
            'expires_at': user.expires_at.isoformat() if user.expires_at else None,
            'is_temporary': user.is_temporary,
            'password_expired': password_expired,
            'password_expires_at': user.password_expires_at.isoformat() if user.password_expires_at else None
        }
    return None

def get_user_by_id(user_id):
    """根据用户ID获取用户

    Args:
        user_id: 用户ID

    Returns:
        dict: 用户信息，如果不存在返回None
    """
    session = get_session()
    user = session.query(User).filter_by(id=user_id).first()
    if user:
        # 检查账号是否过期
        if user.expires_at and user.expires_at < datetime.now() and user.active:
            user.active = False
            session.commit()
        
        # 检查密码是否过期
        password_expired = False
        if user.password_expires_at and user.password_expires_at < datetime.now():
            password_expired = True
        
        return {
            'id': user.id,
            'username': user.username,
            'password_hash': user.password_hash,
            'role': user.role,
            'created_at': user.created_at.isoformat(),
            'last_login': user.updated_at.isoformat() if user.updated_at else None,
            'is_active': user.active,
            'expires_at': user.expires_at.isoformat() if user.expires_at else None,
            'is_temporary': user.is_temporary,
            'password_expired': password_expired,
            'password_expires_at': user.password_expires_at.isoformat() if user.password_expires_at else None
        }
    return None

def create_user(username, password, role='user', expires_in=None, is_temporary=False):
    """创建新用户

    Args:
        username: 用户名
        password: 密码
        role: 角色 ('admin' 或 'user')
        expires_in: 过期时间（秒），None 表示永不过期
        is_temporary: 是否为临时账号

    Returns:
        tuple: (成功标志, 消息)
    """
    session = get_session()

    if session.query(User).filter_by(username=username).first():
        return False, "用户名已存在"

    if role not in USER_ROLES:
        return False, "无效的角色"

    new_user = User(
        username=username,
        password_hash=hash_password(password),
        role=role,
        active=True,
        is_temporary=is_temporary
    )

    if expires_in:
        from datetime import datetime, timedelta
        new_user.expires_at = datetime.now() + timedelta(seconds=expires_in)

    session.add(new_user)
    session.commit()

    return True, "用户创建成功"

def authenticate_user(username, password):
    """验证用户登录

    Args:
        username: 用户名
        password: 密码

    Returns:
        tuple: (成功标志, 用户信息或错误消息)
    """
    session = get_session()
    user = session.query(User).filter_by(username=username).first()

    if not user:
        return False, "用户名或密码错误"

    if not user.active:
        return False, "账户已被禁用"

    # 检查账号是否过期
    if user.expires_at and user.expires_at < datetime.now():
        user.active = False
        session.commit()
        return False, "账户已过期"

    if not verify_password(password, user.password_hash):
        return False, "用户名或密码错误"

    # 更新最后登录时间
    user.updated_at = datetime.now()
    session.commit()

    # 检查密码是否过期
    password_expired = False
    if user.password_expires_at and user.password_expires_at < datetime.now():
        password_expired = True

    return True, {
        'id': user.id,
        'username': user.username,
        'password_hash': user.password_hash,
        'role': user.role,
        'created_at': user.created_at.isoformat(),
        'last_login': user.updated_at.isoformat(),
        'is_active': user.active,
        'expires_at': user.expires_at.isoformat() if user.expires_at else None,
        'is_temporary': user.is_temporary,
        'password_expired': password_expired,
        'password_expires_at': user.password_expires_at.isoformat() if user.password_expires_at else None
    }

def save_user(user):
    """保存用户信息

    Args:
        user: 用户信息字典
    """
    session = get_session()
    db_user = session.query(User).filter_by(username=user['username']).first()
    if db_user:
        db_user.password_hash = user.get('password_hash', db_user.password_hash)
        db_user.role = user.get('role', db_user.role)
        db_user.active = user.get('is_active', db_user.active)
        db_user.updated_at = datetime.now()
        session.commit()

def delete_user(username, current_user_role=None):
    """删除用户

    Args:
        username: 用户名
        current_user_role: 当前用户角色

    Returns:
        tuple: (成功标志, 消息)
    """
    if username == 'Administrator' and current_user_role != 'superadmin':
        return False, "不能删除超级管理员账户"

    session = get_session()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        return False, "用户不存在"

    session.delete(user)
    session.commit()

    return True, "用户删除成功"

def update_user_role(username, new_role, current_user_role=None):
    """更新用户角色

    Args:
        username: 用户名
        new_role: 新角色
        current_user_role: 当前用户角色

    Returns:
        tuple: (成功标志, 消息)
    """
    if username == 'Administrator' and current_user_role != 'superadmin':
        return False, "不能修改超级管理员角色"

    if new_role not in USER_ROLES:
        return False, "无效的角色"

    session = get_session()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        return False, "用户不存在"

    user.role = new_role
    user.updated_at = datetime.now()
    session.commit()

    return True, f"用户角色已更新为 {USER_ROLES[new_role]}"

def toggle_user_status(username, current_user_role=None):
    """切换用户状态

    Args:
        username: 用户名
        current_user_role: 当前用户角色

    Returns:
        tuple: (成功标志, 消息)
    """
    if username == 'Administrator' and current_user_role != 'superadmin':
        return False, "不能修改超级管理员状态"

    session = get_session()
    user = session.query(User).filter_by(username=username).first()
    if not user:
        return False, "用户不存在"

    # 检查临时账号是否过期，过期后不能重新启用
    if user.is_temporary and user.expires_at and user.expires_at < datetime.now():
        return False, "临时账号已过期，不能重新启用"

    user.active = not user.active
    user.updated_at = datetime.now()
    session.commit()

    status = "启用" if user.active else "禁用"
    return True, f"用户已{status}"

def is_admin(user):
    """检查用户是否为管理员

    Args:
        user: 用户信息字典

    Returns:
        bool: 是否为管理员或超级管理员
    """
    role = user.get('role')
    return role == 'admin' or role == 'superadmin'

def login_required(f):
    """登录装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """管理员装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('请先登录', 'warning')
            return redirect(url_for('login'))

        user = get_user_by_id(session['user_id'])
        if not user or not is_admin(user):
            flash('需要管理员权限', 'danger')
            return redirect(url_for('index'))

        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """获取当前登录用户

    Returns:
        dict: 当前用户信息，如果未登录返回None
    """
    if 'user_id' not in session:
        return None

    return get_user_by_id(session['user_id'])

def change_password(username, old_password, new_password):
    """修改用户密码

    Args:
        username: 用户名
        old_password: 旧密码
        new_password: 新密码

    Returns:
        tuple: (成功标志, 消息)
    """
    session = get_session()
    user = session.query(User).filter_by(username=username).first()
    
    if not user:
        return False, "用户不存在"
    
    if not verify_password(old_password, user.password_hash):
        return False, "旧密码错误"
    
    if len(new_password) < 6:
        return False, "新密码至少需要6个字符"
    
    user.password_hash = hash_password(new_password)
    user.password_set_at = datetime.now()
    # 设置密码有效期为90天
    user.password_expires_at = datetime.now() + timedelta(days=90)
    user.updated_at = datetime.now()
    session.commit()
    
    return True, "密码修改成功"

def reset_password(username, new_password):
    """重置用户密码（管理员功能）

    Args:
        username: 用户名
        new_password: 新密码

    Returns:
        tuple: (成功标志, 消息)
    """
    session = get_session()
    user = session.query(User).filter_by(username=username).first()
    
    if not user:
        return False, "用户不存在"
    
    if len(new_password) < 6:
        return False, "新密码至少需要6个字符"
    
    user.password_hash = hash_password(new_password)
    user.password_set_at = datetime.now()
    # 设置密码有效期为90天
    user.password_expires_at = datetime.now() + timedelta(days=90)
    user.updated_at = datetime.now()
    session.commit()
    
    return True, "密码重置成功"

# 兼容旧函数名
def init_users_file():
    """初始化用户数据文件（兼容旧函数）"""
    init_users()