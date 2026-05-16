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
from utils.favorites import get_favorites, is_favorited, add_favorite, remove_favorite, get_favorite_count
from utils.writing_prompts import get_random_prompt, get_prompt_by_mood, get_all_categories, get_seasonal_prompt, get_time_based_prompt, get_prompts_by_category

# Magic bytes for image validation
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

# 导入问候语模块
from utils.greeting import get_combined_greeting, format_greeting

# 导入打卡模块
from utils.streak import (
    update_streak_on_entry,
    get_user_streak_info,
    get_streak_message,
    get_streak_reward,
    recalculate_all_user_streaks
)

# 导入年度回顾模块
from utils.yearly_review import get_yearly_review

# 导入习惯分析模块
from utils.habits import (
    get_writing_heatmap,
    get_best_writing_time,
    get_writing_streak_analysis,
    get_monthly_completion,
    get_year_summary
)

# 导入回忆模块
from utils.memories import get_same_day_last_years, get_milestone_entries

# 导入挑战模块
from utils.challenges import (
    start_challenge,
    get_active_challenge,
    abandon_challenge,
    get_all_challenges_status
)

# 环境配置
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
            # 如果只设置了 SECRET_KEY，重用它作为 CSRF 密钥
            cls.WTF_CSRF_SECRET_KEY = cls.SECRET_KEY

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
            return redirect(url_for('login'))
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
    return redirect(url_for('index'))

@app.errorhandler(500)
def internal_error(error):
    """500 错误处理"""
    logger.error(f"Internal Error: {error}")
    flash('服务器内部错误', 'danger')
    return redirect(url_for('index'))

@app.errorhandler(Exception)
def handle_exception(error):
    """通用异常处理"""
    logger.exception(f"Unhandled Exception: {error}")
    flash('发生未知错误', 'danger')
    return redirect(url_for('index'))

def get_entries():
    db_session = get_session()
    entries = db_session.query(Entry).order_by(Entry.date_str.desc()).all()
    # 返回模拟的文件路径对象，保持向后兼容
    class MockPath:
        def __init__(self, date_str):
            self.stem = date_str
            self.stat = lambda: type('obj', (object,), {'st_size': 0})
    return [MockPath(entry.date_str) for entry in entries]

def get_entry_content(date_str):
    db_session = get_session()
    entry = db_session.query(Entry).filter_by(date_str=date_str).first()
    if entry:
        timestamp = f"[{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]"
        tags = [tag.name for tag in entry.tags]
        content = entry.content
        return timestamp, tags, content
    return None, [], ""

def get_calendar_data(year, month):
    """获取日历数据"""
    from calendar import monthrange, weekday
    from utils.models import get_session, Entry

    # 获取月份的天数和第一天是星期几
    days_in_month = monthrange(year, month)[1]
    first_day_weekday = weekday(year, month, 1)  # 0=Monday, 6=Sunday

    # 调整为 0=Sunday, 6=Saturday
    first_day_weekday = (first_day_weekday + 1) % 7

    # 生成日历数据
    calendar_days = []

    # 添加上个月的填充天数
    prev_month_days = first_day_weekday
    if prev_month_days > 0:
        prev_year, prev_month = (year, month-1) if month > 1 else (year-1, 12)
        prev_month_days_total = monthrange(prev_year, prev_month)[1]
        for day in range(prev_month_days_total - prev_month_days + 1, prev_month_days_total + 1):
            calendar_days.append({
                'day': day,
                'month': prev_month,
                'year': prev_year,
                'is_other_month': True,
                'has_entry': False
            })

    # 添加当前月的天数
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    current_day = today.day

    # 从数据库中获取所有日记日期
    db_session = get_session()
    all_entries = db_session.query(Entry.date_str).all()
    entry_dates = set([entry.date_str for entry in all_entries])

    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        is_today = (year == current_year and month == current_month and day == current_day)

        calendar_days.append({
            'day': day,
            'month': month,
            'year': year,
            'is_other_month': False,
            'is_today': is_today,
            'has_entry': date_str in entry_dates,
            'date_str': date_str
        })

    # 添加下个月的填充天数
    total_days = len(calendar_days)
    remaining_days = (7 - (total_days % 7)) % 7
    if remaining_days > 0:
        next_year, next_month = (year, month+1) if month < 12 else (year+1, 1)
        for day in range(1, remaining_days + 1):
            calendar_days.append({
                'day': day,
                'month': next_month,
                'year': next_year,
                'is_other_month': True,
                'has_entry': False
            })

    return calendar_days

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
get_stats = cache.memoize(timeout=300)(get_stats)

# 用户认证路由
@app.route('/login', methods=['GET', 'POST'])
@rate_limit(max_requests=10, window=60)
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        storage = request.form.get('storage', 'local')

        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return redirect(url_for('login'))

        from utils.db_manager import db_manager
        if storage == 'remote' and not db_manager.is_remote_configured():
            flash('远程数据库尚未配置，请先在设置中配置', 'warning')
            return redirect(url_for('login'))

        if storage != db_manager.get_current_db_type():
            try:
                db_manager.switch_database(storage)
                flash(f'已切换到{"云端" if storage == "remote" else "本地"}存储', 'success')
            except Exception as e:
                flash(f'切换存储失败: {str(e)}', 'danger')
                return redirect(url_for('login'))

        # 检查是否被锁定
        from utils.auth import check_login_lockout, record_login_failure, clear_login_failure, get_remaining_attempts
        if not check_login_lockout(username):
            remaining = get_remaining_attempts(username)
            flash(f'登录失败次数过多，请 {remaining//60+1} 分钟后再试', 'danger')
            return redirect(url_for('login'))

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
            
            # 显示问候语通知
            config = get_config()
            greetings_config = config.get('greetings', {})
            if greetings_config.get('enabled', True) and greetings_config.get('show_on_startup', True):
                greeting_data = get_combined_greeting()
                greeting_text = format_greeting(greeting_data['daily_greeting'])
                try:
                    from utils.notification import add_notification
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
            return redirect(url_for('index'))
        else:
            record_login_failure(username)
            remaining = get_remaining_attempts(username)
            flash(f'{result} (剩余尝试次数: {remaining})', 'danger')
            return redirect(url_for('login'))

    if 'user_id' in session:
        return redirect(url_for('index'))

    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
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
            return redirect(url_for('register'))

        if len(username) < 3 or len(username) > 50:
            flash('用户名需要3-50个字符', 'danger')
            return redirect(url_for('register'))

        if len(password) < 8:
            flash('密码至少需要8个字符', 'danger')
            return redirect(url_for('register'))

        if not any(c.isupper() for c in password):
            flash('密码必须包含大写字母', 'danger')
            return redirect(url_for('register'))

        if not any(c.islower() for c in password):
            flash('密码必须包含小写字母', 'danger')
            return redirect(url_for('register'))

        if not any(c.isdigit() for c in password):
            flash('密码必须包含数字', 'danger')
            return redirect(url_for('register'))

        if len(password) > 128:
            flash('密码不能超过128个字符', 'danger')
            return redirect(url_for('register'))

        if password != confirm_password:
            flash('两次输入的密码不一致', 'danger')
            return redirect(url_for('register'))

        from utils.db_manager import db_manager
        if storage == 'remote' and not db_manager.is_remote_configured():
            flash('远程数据库尚未配置，请先在设置中配置', 'warning')
            return redirect(url_for('register'))

        if storage != db_manager.get_current_db_type():
            try:
                db_manager.switch_database(storage)
            except Exception as e:
                flash(f'切换存储失败: {str(e)}', 'danger')
                return redirect(url_for('register'))

        success, message = create_user(username, password)

        if success:
            from utils.auth import authenticate_user
            auth_success, result = authenticate_user(username, password)
            if auth_success:
                session['user_id'] = result['id']
                session['username'] = result['username']
                session['role'] = result['role']
                session['storage_type'] = storage
                session.permanent = True
                flash(f'注册成功！欢迎，{username}！', 'success')
                return redirect(url_for('index'))
            else:
                flash('注册成功，但登录失败，请手动登录', 'warning')
                return redirect(url_for('login'))
        else:
            flash(message, 'danger')
            return redirect(url_for('register'))

    # 如果已经登录，直接跳转到首页
    if 'user_id' in session:
        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/logout')
def logout():
    """用户登出"""
    username = session.get('username', '用户')
    session.clear()
    flash(f'{username} 已退出登录', 'info')
    return redirect(url_for('login'))

@app.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    if request.method == 'POST':
        old_password = request.form.get('old_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if not old_password or not new_password or not confirm_password:
            flash('请输入所有密码字段', 'danger')
            return redirect(url_for('change_password'))

        if new_password != confirm_password:
            flash('两次输入的新密码不一致', 'danger')
            return redirect(url_for('change_password'))

        if len(new_password) < 8:
            flash('新密码至少需要8个字符', 'danger')
            return redirect(url_for('change_password'))

        if not any(c.isupper() for c in new_password):
            flash('新密码必须包含大写字母', 'danger')
            return redirect(url_for('change_password'))

        if not any(c.islower() for c in new_password):
            flash('新密码必须包含小写字母', 'danger')
            return redirect(url_for('change_password'))

        if not any(c.isdigit() for c in new_password):
            flash('新密码必须包含数字', 'danger')
            return redirect(url_for('change_password'))

        from utils.auth import change_password as auth_change_password
        username = session.get('username')
        success, message = auth_change_password(username, old_password, new_password)

        if success:
            session['password_expired'] = False
            flash(message, 'success')
            return redirect(url_for('index'))
        else:
            flash(message, 'danger')
            return redirect(url_for('change_password'))

    return render_template('change_password.html')

@app.route('/')
@app.route('/<int:year>/<int:month>')
@login_required
def index(year=None, month=None):
    if not year or not month:
        today = datetime.now()
        year = today.year
        month = today.month

    db_session = get_session()
    current_user_id = session.get('user_id')
    
    # 使用 joinedload 预加载关联数据，减少N+1查询
    entries = db_session.query(Entry).options(
        joinedload(Entry.tags),
        joinedload(Entry.mood)
    ).filter_by(user_id=current_user_id).order_by(Entry.date_str.desc()).limit(5).all()
    
    tag_data = get_tags()
    calendar_data = get_calendar_data(year, month)
    stats = get_stats()

    prev_month = month - 1
    prev_year = year
    if prev_month < 1:
        prev_month = 12
        prev_year -= 1

    next_month = month + 1
    next_year = year
    if next_month > 12:
        next_month = 1
        next_year += 1

    # 优化：从已加载的最近5篇日记中统计心情（足够展示用）
    mood_stats = {}
    for entry in entries:
        if entry.mood:
            mt = entry.mood.mood_type
            mood_stats[mt] = mood_stats.get(mt, 0) + 1
    
    # 获取问候语
    greeting_data = get_combined_greeting()
    
    # 获取打卡信息
    streak_info = get_user_streak_info(current_user_id)
    streak_message = get_streak_message(streak_info['current_streak'], streak_info['longest_streak'])
    streak_badges = get_streak_reward(streak_info['current_streak'])

    # 获取回忆数据
    memories_data = get_same_day_last_years(current_user_id, years=3)
    milestone_data = get_milestone_entries(current_user_id)

    return render_template('index.html',
                         entries=entries,
                         tags=tag_data,
                         calendar_data=calendar_data,
                         current_year=year,
                         current_month=month,
                         prev_year=prev_year,
                         prev_month=prev_month,
                         next_year=next_year,
                         next_month=next_month,
                         stats=stats,
                         mood_stats=mood_stats,
                         mood_emoji={'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'},
                         mood_labels={'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'},
                         greeting_data=greeting_data,
                         streak_info=streak_info,
                         streak_message=streak_message,
                         streak_badges=streak_badges,
                         memories_data=memories_data,
                         milestone_data=milestone_data)

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    """设置页面"""
    from utils.config import get_config, save_config

    config = get_config()

    if request.method == 'POST':
        # 保存设置
        config['theme'] = request.form.get('theme', 'light')
        config['backup_enabled'] = 'backup_enabled' in request.form
        config['auto_save'] = 'auto_save' in request.form
        config['notifications']['enabled'] = 'notifications_enabled' in request.form
        # 问候语设置
        if 'greetings' not in config:
            config['greetings'] = {}
        config['greetings']['enabled'] = 'greetings_enabled' in request.form
        config['greetings']['show_on_startup'] = 'greetings_show_on_startup' in request.form
        # 问候语来源仅管理员可修改
        if session.get('role') in ['admin', 'superadmin']:
            config['greetings']['source'] = request.form.get('greetings_source', 'local')

        # 处理远程数据库配置
        db_type = request.form.get('db_type', 'postgresql')
        db_host = request.form.get('db_host', '').strip()
        db_port = request.form.get('db_port', '').strip()
        db_name = request.form.get('db_name', '').strip()
        db_user = request.form.get('db_user', '').strip()
        db_password = request.form.get('db_password', '')

        from utils.db_manager import db_manager
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

        # 处理存储位置切换（需要重新登录才能生效）
        storage_location = request.form.get('storage_location', 'local')
        if storage_location != session.get('storage_type', 'local'):
            from utils.db_manager import db_manager
            if storage_location == 'remote' and not db_manager.is_remote_configured():
                flash('远程数据库尚未配置，请先配置远程数据库', 'warning')
            else:
                session['storage_type'] = storage_location
                flash(f'存储位置已设置为{"云端" if storage_location == "remote" else "本地"}，请重新登录生效', 'info')

        save_config(config)
        flash('设置已保存', 'success')
        return redirect(url_for('settings'))

    from utils.db_manager import db_manager
    remote_config = db_manager.load_config().get('remote', {})
    return render_template('settings.html', config=config, remote_config=remote_config)

@app.route('/api/test-database', methods=['POST'])
@login_required
def test_database():
    """测试数据库连接"""
    if session.get('role') not in ['admin', 'superadmin']:
        return jsonify({'success': False, 'message': '只有管理员可以测试数据库连接'}), 403

    db_host = request.json.get('host', '').strip()
    db_port = request.json.get('port', '').strip()
    db_name = request.json.get('database', '').strip()
    db_user = request.json.get('username', '').strip()
    db_password = request.json.get('password', '')
    db_type = request.json.get('type', 'postgresql')

    if not all([db_host, db_name, db_user]):
        return jsonify({'success': False, 'message': '请填写完整的数据库信息'}), 400

    try:
        from sqlalchemy import create_engine
        from sqlalchemy.exc import OperationalError
        from urllib.parse import quote_plus

        port = int(db_port) if db_port else 5432

        encoded_password = quote_plus(db_password)

        if db_type == 'postgresql':
            db_url = f"postgresql://{db_user}:{encoded_password}@{db_host}:{port}/{db_name}"
            engine = create_engine(db_url, connect_args={'connect_timeout': 10})
        elif db_type == 'mysql':
            db_url = f"mysql+pymysql://{db_user}:{encoded_password}@{db_host}:{port}/{db_name}"
            engine = create_engine(db_url, connect_args={'connect_timeout': 10})
        else:
            return jsonify({'success': False, 'message': '不支持的数据库类型'}), 400

        conn = engine.connect()
        conn.close()
        engine.dispose()

        return jsonify({
            'success': True,
            'message': f'成功连接到 {db_type} 数据库',
            'info': {
                'host': db_host,
                'port': port,
                'database': db_name,
                'type': db_type
            }
        }), 200

    except OperationalError as e:
        error_msg = str(e).split('\n')[0]
        return jsonify({
            'success': False,
            'message': f'数据库连接失败: {error_msg}'
        }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'连接错误: {str(e)}'
        }), 500

@app.route('/new', methods=['GET', 'POST'])
@login_required
def new_entry():
    if request.method == 'POST':
        logger.debug("收到新日记保存请求")
        
        date_str = request.form['date']
        tags_str = request.form['tags']
        content = request.form['content']
        template_id = request.form.get('template', '')
        mood_type = request.form.get('mood', 'neutral')
        mood_note = request.form.get('mood_note', '')

        if not date_str or not content:
            flash('日期和内容不能为空', 'danger')
            return redirect(url_for('new_entry'))

        try:
            datetime.strptime(date_str, DATE_FORMAT)
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式', 'danger')
            return redirect(url_for('new_entry'))

        # 验证模板ID
        if template_id:
            import utils.templates as template_module
            valid_templates = template_module.get_all_templates()
            if template_id not in valid_templates:
                flash('无效的模板ID', 'danger')
                return redirect(url_for('new_entry'))

        # 验证心情类型
        import utils.mood as mood_module
        if mood_type not in mood_module.MOOD_TYPES:
            flash('无效的心情类型', 'danger')
            return redirect(url_for('new_entry'))

        # 验证心情备注长度
        if len(mood_note) > 200:
            flash('心情备注长度不能超过200个字符', 'danger')
            return redirect(url_for('new_entry'))

        # 处理模板
        if template_id:
            try:
                content = template_module.render_template(template_id, date_str)
            except Exception as e:
                logger.error(f"模板渲染失败: {e}")

        # 保存日记到数据库
        db_session = get_session()
        current_user_id = session.get('user_id')
        
        logger.debug(f"准备保存日记 - 用户ID: {current_user_id}")

        # 检查是否已存在该日期的日记
        existing_entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=date_str).first()
        if existing_entry:
            logger.debug(f"该日期的日记已存在: {date_str}")
            flash('该日期的日记已存在', 'danger')
            return redirect(url_for('new_entry'))

        # 创建新日记
        entry = Entry(
            user_id=current_user_id,
            date_str=date_str,
            content=content,
            timestamp=datetime.now()
        )
        db_session.add(entry)
        db_session.flush()  # 获取entry.id
        logger.debug(f"日记对象已添加到会话，ID: {entry.id}")

        # 处理标签
        if tags_str:
            logger.debug(f"处理标签: {tags_str}")
            tags = sanitize_tags(tags_str)
            for tag_name in tags:
                if tag_name and validate_tag(tag_name):
                    # 查找或创建标签
                    tag = db_session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db_session.add(tag)
                    entry.tags.append(tag)

        # 保存心情数据
        try:
            mood = Mood(
                entry_id=entry.id,
                mood_type=mood_type,
                note=mood_note
            )
            db_session.add(mood)
        except Exception as e:
            logger.error(f"保存心情数据失败: {e}")

        logger.debug("准备提交事务")
        db_session.commit()
        logger.debug("事务提交成功")

        # 更新打卡统计
        streak_info = None
        try:
            streak_info = update_streak_on_entry(current_user_id, date_str)
            logger.debug(f"打卡统计更新: {streak_info}")
        except Exception as e:
            logger.error(f"更新打卡统计失败: {e}")

        # 添加通知
        try:
            from utils.notification import add_notification
            notification_msg = f'新日记已保存：{date_str}'
            if streak_info and streak_info['current_streak'] > 0:
                notification_msg += f' | 🔥 连续 {streak_info["current_streak"]} 天！'
            
            add_notification(
                message=notification_msg,
                level='success',
                title='日记保存成功'
            )
        except Exception as e:
            logger.error(f"添加通知失败: {e}")

        flash('日记已保存', 'success')
        return redirect(url_for('index'))

    return render_template('new.html', current_date=datetime.now().strftime(DATE_FORMAT))

@app.route('/entry/<date_str>')
@login_required
def view_entry(date_str):
    # 验证日期字符串
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('index'))
    
    timestamp, tags, content = get_entry_content(date_str)
    if content:
        # 获取心情数据
        mood_info = None
        mood_note = ''
        try:
            import utils.mood as mood_module
            mood_data = mood_module.get_mood(date_str)
            mood_type = mood_data.get('mood_type', 'neutral')
            mood_note = mood_data.get('note', '')
            mood_info = mood_module.MOOD_TYPES.get(mood_type, mood_module.MOOD_TYPES['neutral'])
        except Exception as e:
            logger.error(f"获取心情数据失败: {e}")
        
        return render_template('view.html', 
                             date_str=date_str, 
                             timestamp=timestamp, 
                             tags=tags, 
                             content=content,
                             mood_info=mood_info,
                             mood_note=mood_note)
    flash('未找到该日记', 'danger')
    return redirect(url_for('index'))

@app.route('/edit/<date_str>', methods=['GET', 'POST'])
@login_required
def edit_entry(date_str):
    # 验证日期字符串
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('index'))
    
    timestamp, tags, content = get_entry_content(date_str)
    if not content:
        flash('未找到该日记', 'danger')
        return redirect(url_for('index'))

    # 获取心情数据
    current_mood = 'neutral'
    mood_note = ''
    try:
        import utils.mood as mood_module
        mood_data = mood_module.get_mood(date_str)
        current_mood = mood_data.get('mood_type', 'neutral')
        mood_note = mood_data.get('note', '')
    except Exception as e:
        logger.error(f"获取心情数据失败: {e}")

    if request.method == 'POST':
        new_date = request.form['date']
        tags_str = request.form['tags']
        new_content = request.form['content']
        mood_type = request.form.get('mood', 'neutral')
        new_mood_note = request.form.get('mood_note', '')

        if not new_date or not new_content:
            flash('日期和内容不能为空', 'danger')
            return redirect(url_for('edit_entry', date_str=date_str))

        try:
            datetime.strptime(new_date, DATE_FORMAT)
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式', 'danger')
            return redirect(url_for('edit_entry', date_str=date_str))

        # 验证心情类型
        import utils.mood as mood_module
        if mood_type not in mood_module.MOOD_TYPES:
            flash('无效的心情类型', 'danger')
            return redirect(url_for('edit_entry', date_str=date_str))

        # 验证心情备注长度
        if len(new_mood_note) > 200:
            flash('心情备注长度不能超过200个字符', 'danger')
            return redirect(url_for('edit_entry', date_str=date_str))

        # 保存日记到数据库
        db_session = get_session()
        current_user_id = session.get('user_id')

        # 查找原日记
        entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=date_str).first()
        if not entry:
            flash('未找到该日记', 'danger')
            return redirect(url_for('index'))

        # 检查新日期是否已被使用
        if new_date != date_str:
            existing_entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=new_date).first()
            if existing_entry:
                flash('新日期的日记已存在', 'danger')
                return redirect(url_for('edit_entry', date_str=date_str))
            entry.date_str = new_date

        # 更新日记内容
        entry.content = new_content
        entry.timestamp = datetime.now()

        # 更新标签
        entry.tags = []
        if tags_str:
            tags_list = sanitize_tags(tags_str)
            for tag_name in tags_list:
                if tag_name and validate_tag(tag_name):
                    # 查找或创建标签
                    tag = db_session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db_session.add(tag)
                    entry.tags.append(tag)

        # 更新心情数据
        try:
            mood = db_session.query(Mood).filter_by(entry_id=entry.id).first()
            if mood:
                mood.mood_type = mood_type
                mood.note = new_mood_note
            else:
                mood = Mood(
                    entry_id=entry.id,
                    mood_type=mood_type,
                    note=new_mood_note
                )
                db_session.add(mood)
        except Exception as e:
            logger.error(f"保存心情数据失败: {e}")

        db_session.commit()

        # 添加通知
        try:
            from utils.notification import add_notification
            add_notification(
                message=f'日记已更新：{new_date}',
                level='success',
                title='日记更新成功'
            )
        except Exception as e:
            logger.error(f"添加通知失败: {e}")

        flash('日记已更新', 'success')
        return redirect(url_for('view_entry', date_str=new_date))

    return render_template('edit.html', 
                         date_str=date_str, 
                         tags=tags, 
                         content=content,
                         current_mood=current_mood,
                         mood_note=mood_note)

@app.route('/delete/<date_str>', methods=['GET'])
@login_required
def delete_entry_confirm(date_str):
    """显示删除确认页面"""
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('index'))
    
    db_session = get_session()
    current_user_id = session.get('user_id')
    entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=date_str).first()
    
    if not entry:
        flash('未找到该日记', 'danger')
        return redirect(url_for('index'))
    
    # 获取日记信息用于显示
    timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M') if entry.timestamp else ''
    content = entry.content[:200] if entry.content else ''
    
    # 获取心情
    mood_info = None
    mood_note = ''
    if entry.mood:
        mood_info = entry.mood.mood_type
    
    # 获取标签
    tags = [t.name for t in entry.tags]
    
    # 心情信息
    mood_emoji = {'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'}
    mood_label = {'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'}
    
    return render_template('confirm_delete.html', 
                         date_str=date_str,
                         timestamp=timestamp,
                         content=content,
                         mood_info={'emoji': mood_emoji.get(mood_info, '😐'), 'label': mood_label.get(mood_info, '一般')},
                         mood_note=mood_note,
                         tags=tags)

@app.route('/delete/<date_str>', methods=['POST'])
@login_required
def delete_entry(date_str):
    """执行删除操作"""
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('index'))
    
    db_session = get_session()
    current_user_id = session.get('user_id')
    entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=date_str).first()
    if entry:
        db_session.delete(entry)
        db_session.commit()
        flash('日记已删除', 'success')
    else:
        flash('未找到该日记', 'danger')
    return redirect(url_for('index'))

@app.route('/tag/<tag>')
@login_required
def view_tag(tag):
    # 验证标签名称
    if not validate_tag(tag):
        flash('无效的标签名称', 'danger')
        return redirect(url_for('index'))
    
    tag_data = get_tags()
    if tag in tag_data:
        dates = tag_data[tag]
        entries = []
        for date_str in dates:
            # 验证日期字符串
            if validate_date_str(date_str):
                # 创建模拟的文件路径对象，保持向后兼容
                class MockPath:
                    def __init__(self, date_str):
                        self.stem = date_str
                        self.stat = lambda: type('obj', (object,), {'st_size': 0})
                entries.append(MockPath(date_str))
        return render_template('tag.html', tag=tag, entries=entries)
    flash('未找到该标签', 'danger')
    return redirect(url_for('index'))

@app.route('/search', methods=['GET', 'POST'])
@login_required
def search():
    """搜索日记"""
    db_session = get_session()
    current_user_id = session.get('user_id')
    
    # 获取所有标签用于筛选下拉框
    all_tags = [t.name for t in db_session.query(Tag).all()]
    
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        selected_moods = request.form.getlist('moods')
        selected_tag = request.form.get('tag', '').strip()
        
        # 构建查询
        query = db_session.query(Entry).filter_by(user_id=current_user_id)
        
        # 日期范围筛选
        if start_date:
            query = query.filter(Entry.date_str >= start_date)
        if end_date:
            query = query.filter(Entry.date_str <= end_date)
        
        # 关键词筛选
        if keyword:
            query = query.filter(Entry.content.ilike(f'%{keyword}%'))
        
        # 标签筛选 (优化：先获取标签对象，避免全表join)
        if selected_tag:
            tag_obj = db_session.query(Tag).filter_by(name=selected_tag).first()
            if tag_obj:
                query = query.filter(Entry.tags.contains(tag_obj))
        
        # 心情筛选
        if selected_moods:
            query = query.join(Entry.mood).filter(Mood.mood_type.in_(selected_moods))
        
        entries = query.order_by(Entry.date_str.desc()).all()
        
        # 构建结果
        results = []
        for entry in entries:
            content_preview = entry.content[:100] + '...' if len(entry.content) > 100 else entry.content
            results.append({
                'date_str': entry.date_str,
                'content': content_preview,
                'tags': [t.name for t in entry.tags],
                'mood': entry.mood.mood_type if entry.mood else None,
                'size': len(entry.content)
            })
        
        return render_template('search.html', 
                             keyword=keyword,
                             start_date=start_date,
                             end_date=end_date,
                             selected_moods=selected_moods,
                             selected_tag=selected_tag,
                             all_tags=all_tags,
                             results=results)
    
    return render_template('search.html', all_tags=all_tags, results=[])

@app.route('/stats')
@login_required
def stats():
    """统计页面"""
    db_session = get_session()
    current_user_id = session.get('user_id')
    
    # 获取用户的所有日记，预加载标签和心情
    from sqlalchemy.orm import joinedload
    entries = db_session.query(Entry).options(
        joinedload(Entry.tags),
        joinedload(Entry.mood)
    ).filter_by(user_id=current_user_id).all()
    total_entries = len(entries)
    
    # 计算总字数
    total_chars = sum(len(e.content) for e in entries)
    total_words = sum(len(e.content.split()) for e in entries)
    
    # 获取标签统计（优化版本：避免 N+1 查询）
    tag_stats = {}
    for entry in entries:
        for tag in entry.tags:
            tag_stats[tag.name] = tag_stats.get(tag.name, 0) + 1
    tag_stats_list = [{'tag': k, 'count': v} for k, v in sorted(
        tag_stats.items(), key=lambda x: x[1], reverse=True
    )][:10]
    total_tags = len(tag_stats_list)
    
    # 按月统计
    monthly_stats_dict = {}
    for entry in entries:
        month = entry.date_str[:7]
        if month not in monthly_stats_dict:
            monthly_stats_dict[month] = 0
        monthly_stats_dict[month] += 1
    monthly_stats_list = [{'month': m, 'count': c} for m, c in sorted(monthly_stats_dict.items())]
    
    # 心情统计
    mood_stats = {'happy': 0, 'excited': 0, 'calm': 0, 'tired': 0, 'sad': 0, 'angry': 0, 'anxious': 0, 'neutral': 0}
    for entry in entries:
        if entry.mood:
            mood_stats[entry.mood.mood_type] = mood_stats.get(entry.mood.mood_type, 0) + 1
    
    mood_labels = {'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'}
    mood_emoji = {'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'}
    
    # 获取最近30天的心情数据
    mood_trend = []
    from datetime import datetime, timedelta
    today = datetime.now().date()
    
    # 构建日期到日记的映射
    entries_by_date = {e.date_str: e for e in entries}
    
    for i in range(29, -1, -1):
        day = today - timedelta(days=i)
        day_str = day.strftime('%Y-%m-%d')
        entry = entries_by_date.get(day_str)
        if entry and entry.mood:
            mood_trend.append({
                'date': day_str,
                'mood': entry.mood.mood_type,
                'emoji': mood_emoji.get(entry.mood.mood_type, '😐'),
                'label': mood_labels.get(entry.mood.mood_type, '一般')
            })
        else:
            mood_trend.append({
                'date': day_str,
                'mood': None,
                'emoji': '',
                'label': '无记录'
            })
    
    stats_data = {
        'total_entries': total_entries,
        'total_words': total_words,
        'total_chars': total_chars,
        'total_tags': total_tags
    }
    
    return render_template('stats.html', 
                         stats=stats_data,
                         tag_stats=tag_stats_list,
                         monthly_stats=monthly_stats_list,
                         mood_stats=mood_stats,
                         mood_trend=mood_trend)

@app.route('/yearly-review', methods=['GET'])
@login_required
def yearly_review():
    """年度回顾页面"""
    current_user_id = session.get('user_id')
    year = request.args.get('year', datetime.now().year, type=int)
    
    review_data = get_yearly_review(current_user_id, year)
    
    # 提供年份选择（有日记的年份）
    session_db = get_session()
    user_entries = session_db.query(Entry).filter_by(user_id=current_user_id).all()
    available_years = sorted(list(set([int(e.date_str[:4]) for e in user_entries])), reverse=True)
    
    return render_template('yearly_review.html', 
                         review_data=review_data,
                         available_years=available_years,
                         selected_year=year,
                         mood_emoji={'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'},
                         mood_labels={'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'})

@app.route('/habits')
@login_required
def habits():
    """写作习惯分析页面"""
    current_user_id = session.get('user_id')
    year = request.args.get('year', datetime.now().year, type=int)
    
    heatmap_data = get_writing_heatmap(current_user_id, year)
    time_data = get_best_writing_time(current_user_id)
    streak_data = get_writing_streak_analysis(current_user_id)
    monthly_data = get_monthly_completion(current_user_id, year)
    year_data = get_year_summary(current_user_id, year)
    
    return render_template('habits.html',
                         heatmap_data={'heatmap': heatmap_data, 'total_entries': len(heatmap_data), 'dates': set(heatmap_data.keys())},
                         time_data=time_data,
                         streak_data=streak_data,
                         monthly_data=monthly_data,
                         year_data=year_data or {'total_entries': 0, 'total_chars': 0, 'avg_chars': 0},
                         selected_year=year)

@app.route('/challenges')
@login_required
def challenges():
    """写作挑战页面"""
    current_user_id = session.get('user_id')
    
    challenge_status = get_all_challenges_status(current_user_id)
    
    return render_template('challenges.html',
                         challenge_status=challenge_status)

@app.route('/challenges/start', methods=['POST'])
@login_required
def challenges_start():
    """开始挑战"""
    current_user_id = session.get('user_id')
    challenge_id = request.form.get('challenge_id')
    
    result = start_challenge(current_user_id, challenge_id)
    
    if result:
        if result['has_active']:
            flash('你已经有进行中的挑战了！', 'warning')
        else:
            flash(f"开始{result['challenge']['name']}！加油！💪", 'success')
    else:
        flash('挑战不存在', 'danger')
    
    return redirect(url_for('challenges'))

@app.route('/challenges/abandon', methods=['POST'])
@login_required
def challenges_abandon():
    """放弃挑战"""
    current_user_id = session.get('user_id')
    abandon_challenge(current_user_id)
    flash('已放弃当前挑战', 'info')
    return redirect(url_for('challenges'))

@app.route('/reminder', methods=['GET', 'POST'])
@login_required
def reminder():
    """日记提醒设置"""
    current_user_id = session.get('user_id')
    
    if request.method == 'POST':
        reminder_time = request.form.get('reminder_time', '21:00')
        enabled = request.form.get('enabled', 'off') == 'on'
        
        # 保存到用户设置
        from utils.settings import set_user_setting
        set_user_setting(current_user_id, 'reminder_enabled', enabled)
        set_user_setting(current_user_id, 'reminder_time', reminder_time)
        
        flash(f'提醒设置已更新', 'success')
        return redirect(url_for('reminder'))
    
    from utils.settings import get_user_setting
    enabled = get_user_setting(current_user_id, 'reminder_enabled', False)
    reminder_time = get_user_setting(current_user_id, 'reminder_time', '21:00')
    
    return render_template('reminder.html', 
                         enabled=enabled,
                         reminder_time=reminder_time)

@app.route('/upload/image', methods=['POST'])
def upload_image():
    """上传图片"""
    if 'image' not in request.files:
        return {'success': False, 'message': '请选择图片文件'}, 400
    
    image = request.files['image']
    if image.filename == '':
        return {'success': False, 'message': '请选择图片文件'}, 400
    
    # 验证文件类型
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = image.filename.rsplit('.', 1)[-1].lower() if '.' in image.filename else ''
    if ext not in allowed_extensions:
        return {'success': False, 'message': '只支持 PNG、JPG、JPEG、GIF、WebP 格式'}, 400
    
    # 获取日期参数
    date_str = request.form.get('date', datetime.now().strftime(DATE_FORMAT))
    if not validate_date_str(date_str):
        return {'success': False, 'message': '无效的日期格式'}, 400
    
    # 保存图片
    try:
        # 创建日期目录
        date_dir = IMAGES_DIR / date_str
        date_dir.mkdir(exist_ok=True)
        
        # 生成唯一文件名 (使用UUID避免冲突)
        ext = image.filename.rsplit('.', 1)[-1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = date_dir / filename
        
        # 保存图片
        image.save(filepath)
        
        # 验证文件是否为真实的图片 (Magic Number检查)
        if not validate_image_magic(filepath):
            os.remove(filepath)
            return {'success': False, 'message': '文件不是有效的图片'}, 400
        
        # 返回图片路径
        image_url = f"/images/{date_str}/{filename}"
        return {'success': True, 'url': image_url}
        
    except Exception as e:
        logger.error(f"图片上传失败: {e}")
        return {'success': False, 'message': '图片上传失败'}, 500

# 导入/导出相关路由
@app.route('/import-export')
@login_required
def import_export():
    """导入/导出页面"""
    return render_template('import_export.html')

@app.route('/export', methods=['POST'])
def export_data():
    """导出数据"""
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

        # 添加通知
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

        # 添加错误通知
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
    if 'file' not in request.files:
        flash('请选择文件', 'danger')
        return redirect(url_for('import_export'))
    
    file = request.files['file']
    if file.filename == '':
        flash('请选择文件', 'danger')
        return redirect(url_for('import_export'))
    
    try:
        import utils.import_export as ie
        
        # 保存上传的文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as temp:
            temp.write(file.read())
            temp_path = temp.name
        
        # 根据文件类型导入
        file_ext = Path(file.filename).suffix.lower()
        if file_ext == '.json':
            result = ie.import_from_json(temp_path)
        elif file_ext == '.zip':
            result = ie.import_from_zip(temp_path)
        else:
            flash('只支持 JSON 和 ZIP 格式的文件', 'danger')
            return redirect(url_for('import_export'))
        
        # 清理临时文件
        import os
        os.unlink(temp_path)
        
        flash(f'导入成功: {result["success"]} 成功, {result["failed"]} 失败', 'success')
    except Exception as e:
        logger.error(f"导入失败: {e}")
        flash('导入失败', 'danger')
    
    return redirect(url_for('import_export'))

# 通知相关API路由
@app.route('/api/notifications')
@rate_limit(max_requests=30, window=60)
def get_notifications_api():
    """获取通知列表API"""
    from utils.notification import get_notifications, get_unread_count

    limit = request.args.get('limit', 50, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    notifications = get_notifications(limit=limit, unread_only=unread_only)
    unread_count = get_unread_count()

    return {
        'notifications': notifications,
        'unread_count': unread_count
    }

@app.route('/api/notifications/mark-read/<notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    """标记单个通知为已读"""
    from utils.notification import mark_as_read

    success = mark_as_read(notification_id)
    return {'success': success}

@app.route('/api/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """标记所有通知为已读"""
    from utils.notification import mark_all_as_read

    mark_all_as_read()
    return {'success': True}

@app.route('/api/notifications/<notification_id>', methods=['DELETE'])
def delete_notification_api(notification_id):
    """删除单个通知"""
    from utils.notification import delete_notification

    success = delete_notification(notification_id)
    return {'success': success}

@app.route('/api/notifications/clear', methods=['POST'])
def clear_notifications_api():
    """清空所有通知"""
    from utils.notification import clear_all_notifications

    clear_all_notifications()
    return {'success': True}

# 管理员面板路由
@app.route('/admin')
@admin_required
def admin_panel():
    """管理员面板"""
    users = get_users()
    stats = get_stats()

    # 计算用户统计数据
    total_users = len(users)
    active_users = sum(1 for u in users if u.get('is_active', True))
    admin_count = sum(1 for u in users if u.get('role') == 'admin')

    return render_template('admin.html',
                         users=users,
                         stats=stats,
                         total_users=total_users,
                         active_users=active_users,
                         admin_count=admin_count)

@app.route('/admin/user/create', methods=['POST'])
@admin_required
def admin_create_user():
    """管理员创建用户"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    role = request.form.get('role', 'user')

    if not username or not password:
        flash('用户名和密码不能为空', 'danger')
        return redirect(url_for('admin_panel'))

    success, message = create_user(username, password, role)

    if success:
        # 添加通知
        try:
            from utils.notification import add_notification
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

    return redirect(url_for('admin_panel'))

@app.route('/admin/user/<username>/delete', methods=['POST'])
@admin_required
def admin_delete_user(username):
    """管理员删除用户"""
    success, message = delete_user(username)

    if success:
        try:
            from utils.notification import add_notification
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

    return redirect(url_for('admin_panel'))

@app.route('/admin/user/<username>/toggle-status', methods=['POST'])
@admin_required
def admin_toggle_user_status(username):
    """管理员切换用户状态"""
    success, message = toggle_user_status(username)

    if success:
        flash(message, 'success')
    else:
        flash(message, 'danger')

    return redirect(url_for('admin_panel'))

@app.route('/admin/user/<username>/update-role', methods=['POST'])
@admin_required
def admin_update_user_role(username):
    """管理员更新用户角色"""
    new_role = request.form.get('role', 'user')

    success, message = update_user_role(username, new_role)

    if success:
        try:
            from utils.notification import add_notification
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

    return redirect(url_for('admin_panel'))

@app.route('/admin/user/<username>/reset-password', methods=['POST'])
@admin_required
def admin_reset_password(username):
    """管理员重置用户密码"""
    new_password = request.form.get('new_password', '')
    
    if not new_password:
        flash('新密码不能为空', 'danger')
        return redirect(url_for('admin_panel'))
    
    from utils.auth import reset_password
    success, message = reset_password(username, new_password)
    
    if success:
        try:
            from utils.notification import add_notification
            add_notification(
                message=f'用户 {username} 的密码已重置',
                level='info',
                title='密码重置'
            )
        except Exception:
            pass
        # 如果是当前用户的密码被重置，更新session中的密码过期标志
        if username == session.get('username'):
            session['password_expired'] = False
        flash(message, 'success')
    else:
        flash(message, 'danger')
    
    return redirect(url_for('admin_panel'))

# 收藏功能 API
@app.route('/api/favorites')
@login_required
def get_favorites_api():
    """获取收藏列表"""
    user_id = session.get('user_id')
    favorites = get_favorites(user_id)
    return jsonify(favorites)

@app.route('/api/favorites/<date_str>')
@login_required
def check_favorite_api(date_str):
    """检查是否已收藏"""
    user_id = session.get('user_id')
    return jsonify({'favorited': is_favorited(user_id, date_str)})

@app.route('/api/favorites/<date_str>', methods=['POST'])
@login_required
@rate_limit(max_requests=20, window=60)
def add_favorite_api(date_str):
    """添加收藏"""
    from flask_wtf.csrf import validate_csrf, CSRFError
    try:
        validate_csrf(request.headers.get('X-CSRF-Token') or request.form.get('csrf_token'))
    except CSRFError as e:
        logger.warning(f"CSRF验证失败: {str(e)}")
        return jsonify({'error': 'CSRF token missing or invalid'}), 400
    except Exception as e:
        logger.error(f"添加收藏时发生错误: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    user_id = session.get('user_id')
    title = request.json.get('title', '') if request.is_json else request.form.get('title', '')
    success = add_favorite(user_id, date_str, title)
    return jsonify({'success': success})

@app.route('/api/favorites/<date_str>', methods=['DELETE'])
@login_required
@rate_limit(max_requests=20, window=60)
def remove_favorite_api(date_str):
    """移除收藏"""
    from flask_wtf.csrf import validate_csrf, CSRFError
    try:
        validate_csrf(request.headers.get('X-CSRF-Token') or request.form.get('csrf_token'))
    except CSRFError as e:
        logger.warning(f"CSRF验证失败: {str(e)}")
        return jsonify({'error': 'CSRF token missing or invalid'}), 400
    except Exception as e:
        logger.error(f"移除收藏时发生错误: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
    user_id = session.get('user_id')
    success = remove_favorite(user_id, date_str)
    return jsonify({'success': success})

# 写作提示 API
@app.route('/api/prompts')
@login_required
def get_prompts_api():
    """获取写作提示"""
    category = request.args.get('category', 'daily')
    mood = request.args.get('mood', '')
    use_seasonal = request.args.get('seasonal', 'false').lower() == 'true'
    use_time_based = request.args.get('time_based', 'false').lower() == 'true'
    
    if mood:
        prompt = get_prompt_by_mood(mood)
    elif use_seasonal:
        prompt = get_seasonal_prompt()
    elif use_time_based:
        prompt = get_time_based_prompt()
    else:
        prompt = get_random_prompt(category)
    
    return jsonify({
        'prompt': prompt,
        'categories': get_all_categories()
    })

@app.route('/api/prompts/categories')
@login_required
def get_prompt_categories_api():
    """获取所有提示分类"""
    return jsonify(get_all_categories())

@app.route('/api/prompts/batch')
@login_required
def get_batch_prompts_api():
    """批量获取提示"""
    category = request.args.get('category', 'daily')
    count = int(request.args.get('count', 3))
    prompts = get_prompts_by_category(category, count)
    return jsonify(prompts)

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

    # Gunicorn 配置
    bind = os.environ.get('BIND_ADDRESS', '0.0.0.0:5000')
    workers = int(os.environ.get('GUNICORN_WORKERS', 4))
    worker_class = 'sync'
    timeout = 120
    keepalive = 5

    logger.info(f"启动生产服务器 - 绑定地址: {bind}, 工作进程数: {workers}")

    # 使用 Gunicorn 运行
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
    from utils.changelog import changelog_manager, record_update

    version_info = changelog_manager.get_version()
    logger.info(f"应用启动 - 版本: v{version_info.get('version', '1.0.0')}, Build #{version_info.get('build_number', 1)}")

    env = get_env()

    if env == 'production':
        run_production_server()
    else:
        run_development_server()
