from flask import render_template, request, redirect, url_for, flash, session
from utils.auth import (
    authenticate_user,
    create_user,
    change_password as auth_change_password,
    check_login_lockout,
    record_login_failure,
    clear_login_failure,
    get_remaining_attempts,
    login_required
)
from utils.rate_limit import rate_limit
from utils.db_manager import db_manager
from utils.notification import add_notification
from utils.greeting import get_combined_greeting, format_greeting
from utils.config import get_config
from . import auth_bp
import logging

logger = logging.getLogger(__name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=10, window=60)
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        storage = request.form.get('storage', 'local')

        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return redirect(url_for('auth.login'))

        if storage == 'remote' and not db_manager.is_remote_configured():
            flash('远程数据库尚未配置，请先在设置中配置', 'warning')
            return redirect(url_for('auth.login'))

        if storage != db_manager.get_current_db_type():
            try:
                db_manager.switch_database(storage)
                flash(f'已切换到{"云端" if storage == "remote" else "本地"}存储', 'success')
            except Exception as e:
                flash(f'切换存储失败: {str(e)}', 'danger')
                return redirect(url_for('auth.login'))

        if not check_login_lockout(username):
            remaining = get_remaining_attempts(username)
            flash(f'登录失败次数过多，请 {remaining//60+1} 分钟后再试', 'danger')
            return redirect(url_for('auth.login'))

        success, result = authenticate_user(username, password)

        if success:
            clear_login_failure(username)
            session['user_id'] = result['id']
            session['username'] = result['username']
            session['role'] = result['role']
            session['password_expired'] = result.get('password_expired', False)
            session['storage_type'] = storage
            session.permanent = True
            flash(f'欢迎回来，{result["username"]}！', 'success')
            
            config = get_config()
            greetings_config = config.get('greetings', {})
            if greetings_config.get('enabled', True) and greetings_config.get('show_on_startup', True):
                greeting_data = get_combined_greeting()
                greeting_text = format_greeting(greeting_data['daily_greeting'])
                try:
                    add_notification(
                        message=f"{greeting_data['time_greeting']} {greeting_text}",
                        level='info',
                        title='今日问候'
                    )
                except Exception as e:
                    logger.error(f"添加问候语通知失败: {e}")

            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('diary.index'))
        else:
            record_login_failure(username)
            remaining = get_remaining_attempts(username)
            flash(f'{result} (剩余尝试次数: {remaining})', 'danger')
            return redirect(url_for('auth.login'))

    if 'user_id' in session:
        return redirect(url_for('diary.index'))

    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit(max_requests=5, window=180)
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

        if len(password) < 8:
            flash('密码至少需要8个字符', 'danger')
            return redirect(url_for('auth.register'))

        if not any(c.isupper() for c in password):
            flash('密码必须包含大写字母', 'danger')
            return redirect(url_for('auth.register'))

        if not any(c.islower() for c in password):
            flash('密码必须包含小写字母', 'danger')
            return redirect(url_for('auth.register'))

        if not any(c.isdigit() for c in password):
            flash('密码必须包含数字', 'danger')
            return redirect(url_for('auth.register'))

        if len(password) > 128:
            flash('密码不能超过128个字符', 'danger')
            return redirect(url_for('auth.register'))

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return redirect(url_for('auth.register'))

        if storage == 'remote' and not db_manager.is_remote_configured():
            flash('远程数据库尚未配置，请先在设置中配置', 'warning')
            return redirect(url_for('auth.register'))

        if storage != db_manager.get_current_db_type():
            try:
                db_manager.switch_database(storage)
            except Exception as e:
                flash(f'切换存储失败: {str(e)}', 'danger')
                return redirect(url_for('auth.register'))

        success, message = create_user(username, password)

        if success:
            auth_success, result = authenticate_user(username, password)
            if auth_success:
                session['user_id'] = result['id']
                session['username'] = result['username']
                session['role'] = result['role']
                session['storage_type'] = storage
                session.permanent = True
                flash(f'注册成功！欢迎，{username}！', 'success')
                return redirect(url_for('diary.index'))
            else:
                flash('注册成功，但登录失败，请手动登录', 'warning')
                return redirect(url_for('auth.login'))
        else:
            flash(message, 'danger')
            return redirect(url_for('auth.register'))

    if 'user_id' in session:
        return redirect(url_for('diary.index'))

    return render_template('register.html')


@auth_bp.route('/logout')
def logout():
    """用户登出"""
    username = session.get('username', '用户')
    session.clear()
    flash(f'{username} 已退出登录', 'info')
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

        if len(new_password) < 8:
            flash('新密码至少需要8个字符', 'danger')
            return redirect(url_for('auth.change_password'))

        if not any(c.isupper() for c in new_password):
            flash('新密码必须包含大写字母', 'danger')
            return redirect(url_for('auth.change_password'))

        if not any(c.islower() for c in new_password):
            flash('新密码必须包含小写字母', 'danger')
            return redirect(url_for('auth.change_password'))

        if not any(c.isdigit() for c in new_password):
            flash('新密码必须包含数字', 'danger')
            return redirect(url_for('auth.change_password'))

        username = session.get('username')
        success, message = auth_change_password(username, old_password, new_password)

        if success:
            session['password_expired'] = False
            flash(message, 'success')
            return redirect(url_for('diary.index'))
        else:
            flash(message, 'danger')
            return redirect(url_for('auth.change_password'))

    return render_template('change_password.html')
