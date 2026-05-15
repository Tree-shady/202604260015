"""
用户认证路由模块
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from utils.rate_limit import rate_limit
from utils.auth import (
    authenticate_user,
    create_user,
    get_user_by_id,
    change_password as auth_change_password,
    login_required,
    USER_ROLES
)
from utils.models import get_session, User, LoginAttempt
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=30, window=60)
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ip_address = request.remote_addr or 'unknown'
        
        from utils.rate_limit import check_login_lockout, record_login_failure, reset_login_attempts
        
        # 检查是否被锁定
        is_locked, lockout_time = check_login_lockout(ip_address)
        if is_locked:
            flash(f'登录尝试次数过多，请 {lockout_time} 秒后再试', 'danger')
            return render_template('login.html')
        
        # 验证用户
        user = authenticate_user(username, password)
        if user:
            # 检查用户状态
            if not user.is_active:
                flash('您的账户已被禁用，请联系管理员', 'warning')
                return render_template('login.html')
            
            # 检查密码是否过期
            if user.password_expires_at and datetime.now() > user.password_expires_at:
                flash('密码已过期，请修改密码', 'warning')
                session['temp_user_id'] = user.id
                return redirect(url_for('auth.change_password'))
            
            # 重置登录失败次数
            reset_login_attempts(ip_address)
            
            # 设置 session
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.role == 'admin' or user.role == 'superadmin'
            session['role'] = user.role
            
            # 更新最后登录时间
            db_session = get_session()
            db_user = db_session.query(User).filter_by(id=user.id).first()
            if db_user:
                db_user.last_login_at = datetime.now()
                db_session.commit()
                db_session.close()
            
            # 检查是否是首次登录
            if user.password_set_at == user.created_at:
                flash('欢迎首次登录！为了安全，请修改您的密码', 'info')
                return redirect(url_for('auth.change_password'))
            
            flash('登录成功！', 'success')
            return redirect(url_for('index'))
        else:
            # 记录登录失败
            is_locked = record_login_failure(ip_address)
            
            # 记录到数据库
            db_session = get_session()
            attempt = LoginAttempt(
                username=username,
                ip_address=ip_address,
                user_agent=request.headers.get('User-Agent', ''),
                success=False
            )
            db_session.add(attempt)
            db_session.commit()
            db_session.close()
            
            if is_locked:
                flash('登录尝试次数过多，账户已被临时锁定，请稍后再试', 'danger')
            else:
                flash('用户名或密码错误', 'danger')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit(max_requests=20, window=180)
def register():
    """用户注册"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        storage = request.form.get('storage', 'local')

        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return redirect(url_for('auth.register'))

        if len(username) < 3 or len(username) > 50:
            flash('用户名需要3-50个字符', 'danger')
            return redirect(url_for('auth.register'))

        # 使用统一的密码强度验证
        from utils.auth import validate_password_strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            flash(error_msg, 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return redirect(url_for('auth.register'))

        # 检查用户名是否已存在
        from utils.models import User
        db_session = get_session()
        existing_user = db_session.query(User).filter_by(username=username).first()
        if existing_user:
            db_session.close()
            flash('用户名已存在', 'warning')
            return redirect(url_for('auth.register'))

        # 创建用户
        user_id = create_user(username, password, storage)
        db_session.close()

        if user_id:
            flash('注册成功，请登录', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('注册失败，请稍后重试', 'danger')
    
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """用户登出"""
    session.clear()
    flash('已成功退出登录', 'info')
    return redirect(url_for('auth.login'))


@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not old_password or not new_password or not confirm_password:
            flash('请输入所有密码字段', 'danger')
            return redirect(url_for('auth.change_password'))

        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'danger')
            return redirect(url_for('auth.change_password'))

        username = session.get('username')
        success, message = auth_change_password(username, old_password, new_password)

        if success:
            flash(message, 'success')
            if 'temp_user_id' in session:
                session.pop('temp_user_id')
            return redirect(url_for('index'))
        else:
            flash(message, 'danger')
    
    return render_template('change_password.html')
