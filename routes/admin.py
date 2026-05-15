"""
管理路由模块
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import logging

from utils.auth import login_required, admin_required, get_users, delete_user, update_user_role, toggle_user_status, reset_password, USER_ROLES
from utils.models import get_session, Entry, Tag, Mood, User
from utils.config import get_config, save_config
from utils.db_manager import db_manager
from utils.notification import create_system_notification
from utils.streak import recalculate_all_user_streaks
from utils.audit_log import record_audit_log, get_audit_logs

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/admin')
@login_required
@admin_required
def admin():
    """管理首页"""
    return render_template('admin/index.html')


@admin_bp.route('/admin/users')
@login_required
@admin_required
def users():
    """用户管理"""
    users_list = get_users()
    db_session = get_session()
    moods = db_session.query(Mood).all()
    db_session.close()
    
    # 获取统计信息
    stats = {
        'total_users': len(users_list),
        'active_users': sum(1 for u in users_list if u.is_active),
        'admin_users': sum(1 for u in users_list if u.role in ['admin', 'superadmin'])
    }
    
    return render_template('admin/users.html', 
                         users=users_list, 
                         roles=USER_ROLES,
                         stats=stats,
                         moods=moods)


@admin_bp.route('/admin/config')
@login_required
@admin_required
def config():
    """配置管理"""
    current_config = get_config()
    # 检查远程数据库是否已配置
    is_remote_configured = db_manager.is_remote_configured()
    current_db_type = db_manager.get_current_db_type()
    
    # 安全处理密码，不在前端显示
    if current_config.get('database', {}).get('password'):
        current_config['database']['password'] = '******'
    
    return render_template('admin/config.html', 
                         config=current_config,
                         is_remote_configured=is_remote_configured,
                         current_db_type=current_db_type)


@admin_bp.route('/admin/config', methods=['POST'])
@login_required
@admin_required
def save_config_view():
    """保存配置"""
    title = request.form.get('title', '')
    author = request.form.get('author', '')
    version = request.form.get('version', '')
    storage = request.form.get('storage', 'local')
    
    # 获取当前配置
    current_config = get_config()
    
    # 更新配置
    new_config = current_config.copy()
    new_config['title'] = title
    new_config['author'] = author
    new_config['version'] = version
    new_config['storage'] = storage
    
    # 保存配置
    save_config(new_config)
    
    flash('配置保存成功！', 'success')
    return redirect(url_for('admin.config'))


@admin_bp.route('/admin/database')
@login_required
@admin_required
def database():
    """数据库管理"""
    is_remote_configured = db_manager.is_remote_configured()
    current_db_type = db_manager.get_current_db_type()
    
    # 获取数据库统计
    db_session = get_session()
    entry_count = db_session.query(Entry).count()
    tag_count = db_session.query(Tag).count()
    user_count = db_session.query(User).count()
    db_session.close()
    
    stats = {
        'entries': entry_count,
        'tags': tag_count,
        'users': user_count
    }
    
    return render_template('admin/database.html',
                         is_remote_configured=is_remote_configured,
                         current_db_type=current_db_type,
                         stats=stats)


@admin_bp.route('/admin/users/delete/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user_view(user_id):
    """删除用户"""
    if user_id == session.get('user_id'):
        flash('不能删除自己！', 'warning')
        return redirect(url_for('admin.users'))
    
    success, message = delete_user(user_id)
    if success:
        record_audit_log(user_id, 'user_delete', f'删除用户 {user_id}')
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/users/role/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def update_user_role_view(user_id):
    """更新用户角色"""
    role = request.form.get('role', 'user')
    if role not in USER_ROLES:
        flash('无效的角色', 'warning')
        return redirect(url_for('admin.users'))
    
    if user_id == session.get('user_id'):
        flash('不能修改自己的角色！', 'warning')
        return redirect(url_for('admin.users'))
    
    success, message = update_user_role(user_id, role)
    if success:
        record_audit_log(user_id, 'role_change', f'将用户角色改为 {role}')
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/users/toggle/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user_status_view(user_id):
    """切换用户状态"""
    if user_id == session.get('user_id'):
        flash('不能禁用自己！', 'warning')
        return redirect(url_for('admin.users'))
    
    success, message = toggle_user_status(user_id)
    if success:
        record_audit_log(user_id, 'user_toggle', '切换用户状态')
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/users/reset-password/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def reset_password_view(user_id):
    """重置用户密码"""
    new_password = request.form.get('new_password', '')
    success, message = reset_password(user_id, new_password)
    
    if success:
        record_audit_log(user_id, 'password_reset', '管理员重置密码')
        flash(message, 'success')
    else:
        flash(message, 'danger')
    return redirect(url_for('admin.users'))


@admin_bp.route('/admin/database/config', methods=['POST'])
@login_required
@admin_required
def config_remote_db():
    """配置远程数据库"""
    db_type = request.form.get('type', 'postgresql')
    host = request.form.get('host', 'localhost')
    port = request.form.get('port', '5432')
    database = request.form.get('database', 'diary')
    username = request.form.get('username', '')
    password = request.form.get('password', '')
    
    # 验证输入
    if not all([host, database, username]):
        flash('请填写完整的数据库信息！', 'danger')
        return redirect(url_for('admin.database'))
    
    try:
        # 保存配置
        db_manager.set_remote_config(host, int(port), database, username, password, db_type)
        
        # 尝试测试连接
        try:
            # 切换到远程数据库测试
            db_manager.switch_database('remote')
            # 测试成功后切回本地
            db_manager.switch_database('local')
            flash('远程数据库配置成功！', 'success')
        except Exception as e:
            logger.error(f"Failed to test remote DB: {e}")
            flash('配置已保存，但连接测试失败，请检查数据库设置！', 'warning')
        
        record_audit_log(session.get('user_id'), 'db_config', '配置远程数据库')
        
    except Exception as e:
        logger.error(f"Database config error: {e}")
        flash('配置失败：' + str(e), 'danger')
    
    return redirect(url_for('admin.database'))


@admin_bp.route('/admin/database/switch/<db_type>', methods=['POST'])
@login_required
@admin_required
def switch_db(db_type):
    """切换数据库"""
    if db_type not in ['local', 'remote']:
        flash('无效的数据库类型！', 'danger')
        return redirect(url_for('admin.database'))
    
    try:
        if db_type == 'remote' and not db_manager.is_remote_configured():
            flash('请先配置远程数据库！', 'warning')
            return redirect(url_for('admin.database'))
        
        db_manager.switch_database(db_type)
        flash(f'已切换到{"远程" if db_type == "remote" else "本地"}数据库！', 'success')
        
        record_audit_log(session.get('user_id'), 'db_switch', f'切换到{db_type}数据库')
        
    except Exception as e:
        logger.error(f"Database switch error: {e}")
        flash('切换失败：' + str(e), 'danger')
    
    return redirect(url_for('admin.database'))


@admin_bp.route('/admin/notify', methods=['POST'])
@login_required
@admin_required
def send_notification():
    """发送系统通知"""
    message = request.form.get('message', '')
    level = request.form.get('level', 'info')
    
    if not message:
        flash('请输入通知内容！', 'warning')
        return redirect(url_for('admin.admin'))
    
    create_system_notification(message, level)
    flash('通知发送成功！', 'success')
    
    record_audit_log(session.get('user_id'), 'system_notify', '发送系统通知')
    
    return redirect(url_for('admin.admin'))


@admin_bp.route('/admin/recalculate-streaks', methods=['POST'])
@login_required
@admin_required
def recalculate_streaks():
    """重新计算打卡"""
    try:
        count = recalculate_all_user_streaks()
        flash(f'已重新计算 {count} 个用户的打卡记录！', 'success')
        record_audit_log(session.get('user_id'), 'recalculate_streaks', '重新计算打卡记录')
    except Exception as e:
        logger.error(f"Recalculate streaks error: {e}")
        flash('计算失败：' + str(e), 'danger')
    return redirect(url_for('admin.admin'))


@admin_bp.route('/admin/audit-log')
@login_required
@admin_required
def audit_log():
    """审计日志"""
    logs = get_audit_logs(limit=100)
    return render_template('admin/audit_log.html', logs=logs)


@admin_bp.route('/admin/moods')
@login_required
@admin_required
def moods():
    """心情管理"""
    db_session = get_session()
    moods = db_session.query(Mood).all()
    db_session.close()
    
    return render_template('admin/moods.html', moods=moods)


@admin_bp.route('/admin/moods/add', methods=['POST'])
@login_required
@admin_required
def add_mood():
    """添加心情"""
    name = request.form.get('name', '')
    icon = request.form.get('icon', '😊')
    color = request.form.get('color', '#6b7280')
    
    if not name:
        flash('请输入心情名称！', 'warning')
        return redirect(url_for('admin.moods'))
    
    db_session = get_session()
    mood = Mood(name=name, icon=icon, color=color)
    db_session.add(mood)
    db_session.commit()
    db_session.close()
    
    flash('心情添加成功！', 'success')
    return redirect(url_for('admin.moods'))


@admin_bp.route('/admin/moods/delete/<int:mood_id>', methods=['POST'])
@login_required
@admin_required
def delete_mood(mood_id):
    """删除心情"""
    db_session = get_session()
    mood = db_session.query(Mood).filter_by(id=mood_id).first()
    if mood:
        db_session.delete(mood)
        db_session.commit()
        flash('心情删除成功！', 'success')
    db_session.close()
    
    return redirect(url_for('admin.moods'))
