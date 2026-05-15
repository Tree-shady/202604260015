from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory, session, jsonify
from flask_wtf.csrf import CSRFProtect
import os
import sys
import json
import logging
import uuid
import calendar
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy.orm import joinedload
from utils.rate_limit import rate_limiter, rate_limit

load_dotenv()

# 配置
ENTRIES_DIR = Path("entries")
IMAGES_DIR = Path("images")
DATE_FORMAT = "%Y-%m-%d"

# 确保目录存在
ENTRIES_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# 导入数据库模型
from utils.models import init_db, get_session, Entry, Tag, Mood, entry_tags

# 导入验证模块
from utils.validation import validate_date_str, validate_tag, sanitize_tags

# 导入用户认证模块
from utils.auth import (
    authenticate_user,
    create_user,
    get_user_by_username,
    get_user_by_id,
    get_users,
    delete_user,
    update_user_role,
    toggle_user_status,
    is_admin,
    login_required,
    admin_required,
    get_current_user,
    USER_ROLES,
    init_users
)

# 导入配置模块
from utils.config import get_config

# 环境配置
class Config:
    """应用配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'diary-app-secret-key-2026'
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY') or 'diary-csrf-secret-key-2026'
    WTF_CSRF_ENABLED = True

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{Path("diary.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ENTRIES_PER_PAGE = 20

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 天

    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False

    # 生产环境更严格的日志级别
    LOG_LEVEL = logging.WARNING

class TestingConfig(Config):
    """测试环境配置"""
    DEBUG = True
    TESTING = True

# 环境配置映射
config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

# 获取当前环境
def get_env():
    """获取当前运行环境"""
    env = os.environ.get('FLASK_ENV') or os.environ.get('APP_ENV') or 'development'
    return env.lower()

# 获取配置类
def get_config_class():
    """获取当前环境的配置类"""
    env = get_env()
    return config_map.get(env, DevelopmentConfig)

# 创建 Flask 应用
app = Flask(__name__)
config_class = get_config_class()
app.config.from_object(config_class)

# 添加缓存配置
app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300  # 5分钟

# 设置 CSRF 配置
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = app.config.get('SECRET_KEY', 'csrf-secret-key')
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

# 初始化 CSRF 保护
csrf = CSRFProtect()
csrf.init_app(app)

# 导入并注册蓝图
from routes.admin import admin_bp
from routes.api import api_bp
from routes.auth import auth_bp
from routes.main import main_bp
from routes.other import other_bp

app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)
app.register_blueprint(other_bp)

# 设置 CSRF 豁免路由
csrf.exempt('api.add_favorite_api')
csrf.exempt('api.remove_favorite_api')
csrf.exempt('api.mark_notification_read')
csrf.exempt('api.mark_all_notifications_read')
csrf.exempt('api.delete_notification_api')
csrf.exempt('api.clear_notifications_api')
csrf.exempt('other.upload_image')
csrf.exempt('other.export_data')
csrf.exempt('other.import_data')


# 初始化缓存
from flask_caching import Cache
cache = Cache(app)

# 初始化数据库和管理员用户
try:
    init_db(app.config['SQLALCHEMY_DATABASE_URI'])
    init_users()
except Exception as e:
    import logging
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger(__name__)
    logger.error(f"数据库初始化失败: {e}")
    raise

# 设置日志
logging.basicConfig(
    level=app.config['LOG_LEVEL'],
    format=app.config['LOG_FORMAT']
)
logger = logging.getLogger(__name__)

# 会话超时配置
SESSION_TIMEOUT = 1800  # 30分钟

@app.before_request
def check_session_timeout():
    """检查会话是否超时"""
    import time
    if 'user_id' in session:
        last_activity = session.get('last_activity')
        if last_activity and time.time() - last_activity > SESSION_TIMEOUT:
            session.clear()
            flash('会话已超时，请重新登录', 'warning')
            return redirect(url_for('auth.login'))
        session['last_activity'] = time.time()

# 请求日志中间件
@app.before_request
def log_request():
    """记录请求日志"""
    if app.config['DEBUG']:
        logger.debug(f"Request: {request.method} {request.path}")

@app.after_request
def log_response(response):
    """记录响应日志"""
    if app.config['DEBUG']:
        logger.debug(f"Response: {response.status_code}")
    return response

@app.after_request
def add_security_headers(response):
    """添加安全头"""
    from utils.security_headers import add_security_headers as apply_security_headers
    return apply_security_headers(response)

@app.teardown_request
def teardown_request(exception):
    """请求结束后关闭数据库会话"""
    from utils.models import close_db
    try:
        close_db()
    except Exception as e:
        logger.error(f"关闭数据库会话时出错: {e}")

# 安全工具函数
@cache.memoize(timeout=300)
def get_tags():
    db_session = get_session()
    tags = db_session.query(Tag).all()
    return {tag.name: [entry.date_str for entry in tag.entries] for tag in tags}

def save_tags(tags):
    pass

@app.errorhandler(404)
def not_found_error(error):
    """404 错误处理"""
    flash('页面未找到', 'warning')
    return redirect(url_for('main.index'))

@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    logger.error(f"Internal Error: {error}")
    flash('服务器内部错误', 'danger')
    return redirect(url_for('main.index'))

@app.errorhandler(Exception)
def handle_exception(error):
    """通用异常处理"""
    logger.exception(f"Unhandled Exception: {error}")
    flash('发生未知错误', 'danger')
    return redirect(url_for('main.index'))

try:
    from flask_wtf.csrf import CSRFError
    
    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        """CSRF 错误处理"""
        logger.warning(f"CSRF Error: {error}")
        
        # 检查是否是 AJAX 请求
        if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'error': 'CSRF 令牌无效或已过期',
                'message': '请刷新页面后重试',
                'code': 'csrf_error'
            }), 400
        
        flash('CSRF 令牌无效或已过期，请刷新页面后重试', 'warning')
        return redirect(url_for('main.index'))
except ImportError:
    pass

if __name__ == '__main__':
    from utils.changelog import changelog_manager, record_update
    from utils.server_config import run_development_server, run_production_server

    version_info = changelog_manager.get_version()
    logger.info(f"应用启动 - 版本: v{version_info.get('version', '1.0.0')}, Build #{version_info.get('build_number', 1)}")

    env = get_env()

    if env == 'production':
        run_production_server(app)
    else:
        run_development_server(app)
