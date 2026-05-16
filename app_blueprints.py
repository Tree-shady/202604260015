from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_wtf.csrf import CSRFProtect
from dotenv import load_dotenv
import os
import logging
from pathlib import Path
from datetime import datetime

load_dotenv()

ENTRIES_DIR = Path("entries")
IMAGES_DIR = Path("images")
ENTRIES_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

from utils.models import init_db, get_session
from utils.auth import init_users
from utils.config import get_config

IMAGE_MAGIC = {
    'jpeg': [b'\xff\xd8\xff'],
    'png': [b'\x89PNG'],
    'gif': [b'GIF87a', b'GIF89a'],
    'webp': [b'RIFF'],
}


def validate_image_magic(filepath):
    """Validate image by checking magic bytes"""
    try:
        with open(filepath, 'rb') as f:
            header = f.read(16)
        for img_type, magics in IMAGE_MAGIC.items():
            for magic in magics:
                if header.startswith(magic):
                    if img_type == 'jpeg':
                        return 'jpeg'
                    elif img_type == 'png':
                        return 'png'
                    elif img_type == 'gif':
                        return 'gif'
                    elif img_type == 'webp':
                        if b'WEBP' in header[:12]:
                            return 'webp'
        return None
    except:
        return None


class Config:
    """应用配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY')
    WTF_CSRF_SECRET_KEY = os.environ.get('WTF_CSRF_SECRET_KEY')
    WTF_CSRF_ENABLED = True
    
    @classmethod
    def validate_config(cls):
        """验证关键配置项是否已设置"""
        if not cls.SECRET_KEY:
            raise RuntimeError("SECRET_KEY 环境变量未设置！")
        if not cls.WTF_CSRF_SECRET_KEY:
            cls.WTF_CSRF_SECRET_KEY = cls.SECRET_KEY

    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{Path("diary.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ENTRIES_PER_PAGE = 20
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024
    PERMANENT_SESSION_LIFETIME = 86400 * 7
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    LOG_LEVEL = logging.WARNING


class TestingConfig(Config):
    DEBUG = True
    TESTING = True


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_env():
    """获取当前运行环境"""
    env = os.environ.get('FLASK_ENV') or os.environ.get('APP_ENV') or 'development'
    return env.lower()


def get_config_class():
    """获取当前环境的配置类"""
    env = get_env()
    return config_map.get(env, DevelopmentConfig)


app = Flask(__name__)
config_class = get_config_class()

try:
    config_class.validate_config()
except RuntimeError as e:
    import sys
    print(f"配置错误: {e}", file=sys.stderr)
    print("\n请在 .env 文件中设置以下变量：", file=sys.stderr)
    print("  SECRET_KEY=your-secret-key-here", file=sys.stderr)
    print("  ADMIN_PASSWORD=your-admin-password-here", file=sys.stderr)
    sys.exit(1)

app.config.from_object(config_class)

app.config['CACHE_TYPE'] = 'SimpleCache'
app.config['CACHE_DEFAULT_TIMEOUT'] = 300
app.config['WTF_CSRF_ENABLED'] = True
app.config['WTF_CSRF_SECRET_KEY'] = app.config.get('SECRET_KEY', 'csrf-secret-key')
app.config['WTF_CSRF_TIME_LIMIT'] = 3600

csrf = CSRFProtect()
csrf.init_app(app)

from flask_caching import Cache
cache = Cache(app)

try:
    init_db(app.config['SQLALCHEMY_DATABASE_URI'])
    init_users()
except Exception as e:
    logging.basicConfig(level=logging.ERROR)
    logger = logging.getLogger(__name__)
    logger.error(f"数据库初始化失败: {e}")
    raise

logging.basicConfig(
    level=app.config['LOG_LEVEL'],
    format=app.config['LOG_FORMAT']
)
logger = logging.getLogger(__name__)

SESSION_TIMEOUT = 1800


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


@app.teardown_request
def teardown_request(exception):
    """请求结束后关闭数据库会话"""
    from utils.models import close_db
    try:
        close_db()
    except Exception as e:
        logger.error(f"关闭数据库会话时出错: {e}")


@app.errorhandler(404)
def not_found_error(error):
    """404 错误处理"""
    flash('页面未找到', 'warning')
    return redirect(url_for('diary.index'))


@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    logger.error(f"Internal Error: {error}")
    flash('服务器内部错误', 'danger')
    return redirect(url_for('diary.index'))


@app.errorhandler(Exception)
def handle_exception(error):
    """通用异常处理"""
    logger.exception(f"Unhandled Exception: {error}")
    flash('发生未知错误', 'danger')
    return redirect(url_for('diary.index'))


@cache.memoize(timeout=300)
def get_tags():
    """获取所有标签（带缓存）"""
    db_session = get_session()
    from utils.models import Tag
    tags = db_session.query(Tag).all()
    return {tag.name: [entry.date_str for entry in tag.entries] for tag in tags}


app.jinja_env.globals['get_tags'] = get_tags


from blueprints.auth import auth_bp
from blueprints.diary import diary_bp
from blueprints.admin import admin_bp
from blueprints.api import api_bp
from blueprints.settings import settings_bp
from blueprints.search import search_bp

app.register_blueprint(auth_bp)
app.register_blueprint(diary_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(api_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(search_bp)


@app.route('/import-export')
def import_export():
    """导入/导出页面"""
    from utils.auth import login_required
    from flask import session
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('import_export.html')


@app.route('/export', methods=['POST'])
def export_data():
    """导出数据"""
    from utils.auth import login_required
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    export_format = request.form.get('format')
    
    try:
        import utils.import_export as ie
        
        if export_format == 'json':
            file_path = ie.export_to_json()
        elif export_format == 'csv':
            file_path = ie.export_to_csv()
        elif export_format == 'markdown':
            file_path = ie.export_to_markdown()
        elif export_format == 'zip':
            file_path = ie.export_to_zip()
        else:
            flash('无效的导出格式', 'danger')
            return redirect(url_for('import_export'))
        
        flash(f'导出成功，文件保存至: {file_path}', 'success')

        try:
            from utils.notification import add_notification
            add_notification(
                message=f'数据已成功导出为 {export_format.upper()} 格式',
                level='success',
                title='导出成功'
            )
        except Exception as e:
            logger.error(f"添加通知失败: {e}")
    except Exception as e:
        logger.error(f"导出失败: {e}")
        flash('导出失败', 'danger')

        try:
            from utils.notification import add_notification
            add_notification(
                message=f'导出失败：{str(e)}',
                level='error',
                title='导出失败'
            )
        except Exception:
            pass
    
    return redirect(url_for('import_export'))


@app.route('/import', methods=['POST'])
def import_data():
    """导入数据"""
    from utils.auth import login_required
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    
    if 'file' not in request.files:
        flash('请选择文件', 'danger')
        return redirect(url_for('import_export'))
    
    file = request.files['file']
    if file.filename == '':
        flash('请选择文件', 'danger')
        return redirect(url_for('import_export'))
    
    try:
        import utils.import_export as ie
        import tempfile
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp:
            temp.write(file.read())
            temp_path = temp.name
        
        file_ext = Path(file.filename).suffix.lower()
        if file_ext == '.json':
            result = ie.import_from_json(temp_path)
        elif file_ext == '.zip':
            result = ie.import_from_zip(temp_path)
        else:
            flash('只支持 JSON 和 ZIP 格式的文件', 'danger')
            return redirect(url_for('import_export'))
        
        import os
        os.unlink(temp_path)
        
        flash(f'导入成功: {result["success"]} 成功, {result["failed"]} 失败', 'success')
    except Exception as e:
        logger.error(f"导入失败: {e}")
        flash('导入失败', 'danger')
    
    return redirect(url_for('import_export'))


def run_production_server():
    """运行生产服务器"""
    if not os.environ.get('SECRET_KEY'):
        logger.warning("生产环境未设置 SECRET_KEY 环境变量，使用默认值")

    try:
        from gunicorn.app.wsgiapp import WSGIApplication
    except ImportError:
        logger.warning("Gunicorn 未安装，将使用 Flask 内置服务器")
        run_development_server()
        return

    bind = os.environ.get('BIND_ADDRESS', '0.0.0.0:5000')
    workers = int(os.environ.get('GUNICORN_WORKERS', 4))
    worker_class = 'sync'
    timeout = 120
    keepalive = 5

    logger.info(f"启动生产服务器 - 绑定地址: {bind}, 工作进程数: {workers}")

    app_for_gunicorn = WSGIApplication()
    app_for_gunicorn.load_wsgiapp()
    app_for_gunicorn.cfg.set({
        'bind': bind,
        'workers': workers,
        'worker_class': worker_class,
        'timeout': timeout,
        'keepalive': keepalive,
        'accesslog': '-',
        'errorlog': '-',
        'loglevel': 'info'
    })
    app_for_gunicorn.run()


def run_development_server():
    """运行开发服务器"""
    host = os.environ.get('FLASK_HOST', '0.0.0.0')
    port = int(os.environ.get('FLASK_PORT', 5000))

    logger.info(f"启动开发服务器 - 地址: http://{host}:{port}")
    print(f"\n{'=' * 60}")
    print(f"  日记本 Web 服务器")
    print(f"{'=' * 60}")
    print(f"  开发模式: http://127.0.0.1:{port}")
    print(f"  生产模式: 请设置 FLASK_ENV=production")
    print(f"{'=' * 60}\n")

    app.run(host=host, port=port, debug=True)


if __name__ == '__main__':
    from utils.changelog import changelog_manager

    version_info = changelog_manager.get_version()
    logger.info(f"应用启动 - 版本: v{version_info.get('version', '1.0.0')}, Build #{version_info.get('build_number', 1)}")

    env = get_env()

    if env == 'production':
        run_production_server()
    else:
        run_development_server()
