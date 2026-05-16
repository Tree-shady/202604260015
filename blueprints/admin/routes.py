from flask import render_template, request, redirect, url_for, flash, session
from utils.auth import (
    get_users,
    create_user,
    delete_user,
    update_user_role,
    toggle_user_status,
    admin_required
)
from utils.notification import add_notification
from utils.models import get_session, Entry, Tag
from . import admin_bp
import logging

logger = logging.getLogger(__name__)


def get_stats():
    """获取统计数据"""
    db_session = get_session()
    entries = db_session.query(Entry).all()
    total_entries = len(entries)

    total_words = sum(len(e.content.split()) for e in entries)
    total_chars = sum(len(e.content) for e in entries)

    tags = db_session.query(Tag).all()
    total_tags = len(tags)

    return {
        'total_entries': total_entries,
        'total_words': total_words,
        'total_chars': total_chars,
        'total_tags': total_tags
    }


@admin_bp.route('/')
@admin_required
def admin_panel():
    """管理员面板"""
    users = get_users()
    stats = get_stats()

    total_users = len(users)
    active_users = sum(1 for u in users if u.get('is_active', True))
    admin_count = sum(1 for u in users if u.get('role') == 'admin')

    return render_template('admin.html',
                         users=users,
                         stats=stats,
                         total_users=total_users,
                         active_users=active_users,
                         admin_count=admin_count)


@admin_bp.route('/user/create', methods=['POST'])
@admin_required
def admin_create_user():
    """管理员创建用户"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'user')

    if not username or not password:
        flash('用户名和密码不能为空', 'danger')
        return redirect(url_for('admin.admin_panel'))

    success, message = create_user(username, password, role)

    if success:
        try:
            add_notification(
                message=f'管理员创建了新用户：{username}',
                level='info',
                title='用户创建'
            )
        except Exception:
            pass
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/user/<username>/delete', methods=['POST'])
@admin_required
def admin_delete_user(username):
    """管理员删除用户"""
    success, message = delete_user(username)

    if success:
        try:
            add_notification(
                message=f'用户已被删除：{username}',
                level='warning',
                title='用户删除'
            )
        except Exception:
            pass
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/user/<username>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(username):
    """管理员切换用户状态"""
    success, message = toggle_user_status(username)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/user/<username>/update-role', methods=['POST'])
@admin_required
def admin_update_user_role(username):
    """管理员更新用户角色"""
    new_role = request.form.get('role', 'user')

    success, message = update_user_role(username, new_role)

    if success:
        try:
            add_notification(
                message=f'用户 {username} 的角色已更新为 {new_role}',
                level='info',
                title='权限更新'
            )
        except Exception:
            pass
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('admin.admin_panel'))


@admin_bp.route('/user/<username>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(username):
    """管理员重置用户密码"""
    new_password = request.form.get('new_password', '')
    
    if not new_password:
        flash('新密码不能为空', 'danger')
        return redirect(url_for('admin.admin_panel'))
    
    from utils.auth import reset_password
    success, message = reset_password(username, new_password)
    
    if success:
        try:
            add_notification(
                message=f'用户 {username} 的密码已重置',
                level='info',
                title='密码重置'
            )
        except Exception:
            pass
        if username == session.get('username'):
            session['password_expired'] = False
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('admin.admin_panel'))
