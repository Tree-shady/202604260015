from flask import render_template, request, redirect, url_for, flash, session, jsonify
from utils.auth import login_required
from utils.config import get_config, save_config
from utils.db_manager import db_manager
from . import settings_bp
import logging

logger = logging.getLogger(__name__)


@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def settings():
    """设置页面"""
    config = get_config()

    if request.method == 'POST':
        config['theme'] = request.form.get('theme', 'light')
        config['backup_enabled'] = 'backup_enabled' in request.form
        config['auto_save'] = 'auto_save' in request.form
        config['notifications']['enabled'] = 'notifications_enabled' in request.form
        
        if 'greetings' not in config:
            config['greetings'] = {}
        config['greetings']['enabled'] = 'greetings_enabled' in request.form
        config['greetings']['show_on_startup'] = 'greetings_show_on_startup' in request.form
        
        if session.get('role') in ['admin', 'superadmin']:
            config['greetings']['source'] = request.form.get('greetings_source', 'local')

        db_type = request.form.get('db_type', 'postgresql')
        db_host = request.form.get('db_host', '').strip()
        db_port = request.form.get('db_port', '').strip()
        db_name = request.form.get('db_name', '').strip()
        db_user = request.form.get('db_user', '').strip()
        db_password = request.form.get('db_password', '')

        current_remote_config = db_manager.load_config().get('remote', {})

        if any([db_host, db_port, db_name, db_user, db_password]):
            try:
                port = int(db_port) if db_port else current_remote_config.get('port', 5432)
                host = db_host if db_host else current_remote_config.get('host', '')
                database = db_name if db_name else current_remote_config.get('database', '')
                username = db_user if db_user else current_remote_config.get('username', '')
                password = db_password if db_password else current_remote_config.get('password', '')
                db_type = db_type if db_type else current_remote_config.get('type', 'postgresql')

                if host and database and username:
                    db_manager.set_remote_config(host, port, database, username, password, db_type)
                    flash('远程数据库配置已保存', 'success')
                else:
                    flash('远程数据库配置不完整，请填写完整信息', 'warning')
            except Exception as e:
                flash(f'保存远程数据库配置失败: {str(e)}', 'danger')

        storage_location = request.form.get('storage_location', 'local')
        if storage_location != session.get('storage_type', 'local'):
            if storage_location == 'remote' and not db_manager.is_remote_configured():
                flash('远程数据库尚未配置，请先配置远程数据库', 'warning')
            else:
                session['storage_type'] = storage_location
                flash(f'存储位置已设置为{"云端" if storage_location == "remote" else "本地"}，请重新登录生效', 'info')

        save_config(config)
        flash('设置已保存', 'success')
        return redirect(url_for('settings.settings'))

    remote_config = db_manager.load_config().get('remote', {})
    return render_template('settings.html', config=config, remote_config=remote_config)
