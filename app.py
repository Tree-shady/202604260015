from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path

# 配置
ENTRIES_DIR = Path("entries")
IMAGES_DIR = Path("images")
DATE_FORMAT = "%Y-%m-%d"
TAGS_FILE = Path("tags.json")

# 确保目录存在
ENTRIES_DIR.mkdir(exist_ok=True)
IMAGES_DIR.mkdir(exist_ok=True)

# 环境配置
class Config:
    """应用配置类"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'diary-app-secret-key-2026'

    # 数据库配置（如果有）
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{Path("diary.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 分页配置
    ENTRIES_PER_PAGE = 20

    # 上传配置
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # Session 配置
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 7 天

    # 日志配置
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

# 设置日志
logging.basicConfig(
    level=app.config['LOG_LEVEL'],
    format=app.config['LOG_FORMAT']
)
logger = logging.getLogger(__name__)

# 初始化标签文件
def init_tags_file():
    if not TAGS_FILE.exists():
        with open(TAGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

init_tags_file()

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

# 安全工具函数
def validate_date_str(date_str):
    """验证日期字符串，防止路径遍历攻击"""
    import re
    # 验证日期格式：YYYY-MM-DD
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
    # 验证日期是否有效
    try:
        datetime.strptime(date_str, DATE_FORMAT)
        return True
    except ValueError:
        return False

def validate_tag(tag):
    """验证标签名称，防止恶意输入"""
    import re
    # 标签只能包含字母、数字、中文、下划线、连字符
    if not re.match(r'^[\w\u4e00-\u9fa5-]+$', tag):
        return False
    # 标签长度限制
    if len(tag) > 50:
        return False
    return True

# 错误处理器
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

def get_tags():
    with open(TAGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_tags(tags):
    with open(TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

def get_entries():
    return sorted(ENTRIES_DIR.glob("*.txt"), reverse=True)

def get_entry_content(date_str):
    file_path = ENTRIES_DIR / f"{date_str}.txt"
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 提取标签和内容
        lines = content.split('\n')
        tags = []
        timestamp = ""

        if lines and lines[0].startswith("[") and "]" in lines[0]:
            timestamp = lines[0]
            lines = lines[1:]

        if lines and lines[0].startswith("Tags: "):
            tags_str = lines[0][6:]
            tags = [tag.strip() for tag in tags_str.split(',')]
            lines = lines[1:]

        content = '\n'.join(lines)
        return timestamp, tags, content
    return None, [], ""

def get_calendar_data(year, month):
    """获取日历数据"""
    from calendar import monthrange, weekday

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

    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        file_path = ENTRIES_DIR / f"{date_str}.txt"
        is_today = (year == current_year and month == current_month and day == current_day)

        calendar_days.append({
            'day': day,
            'month': month,
            'year': year,
            'is_other_month': False,
            'is_today': is_today,
            'has_entry': file_path.exists(),
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
    entries = get_entries()
    total_entries = len(entries)

    # 计算总字数
    total_words = 0
    total_chars = 0

    for entry in entries:
        with open(entry, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            # 移除时间戳和标签行
            if lines and lines[0].startswith("[") and "]" in lines[0]:
                lines = lines[1:]
            if lines and lines[0].startswith("Tags: "):
                lines = lines[1:]
            content = '\n'.join(lines)
            total_chars += len(content)
            total_words += len(content.split())

    # 获取标签统计
    tag_data = get_tags()
    total_tags = len(tag_data)

    return {
        'total_entries': total_entries,
        'total_words': total_words,
        'total_chars': total_chars,
        'total_tags': total_tags
    }

@app.route('/')
@app.route('/<int:year>/<int:month>')
def index(year=None, month=None):
    if not year or not month:
        today = datetime.now()
        year = today.year
        month = today.month

    entries = get_entries()
    tag_data = get_tags()
    calendar_data = get_calendar_data(year, month)
    stats = get_stats()

    # 计算上一个月和下一个月
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
                         stats=stats)

@app.route('/settings', methods=['GET', 'POST'])
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

        save_config(config)
        flash('设置已保存', 'success')
        return redirect(url_for('settings'))

    return render_template('settings.html', config=config)

@app.route('/new', methods=['GET', 'POST'])
def new_entry():
    if request.method == 'POST':
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
            valid_templates = template_module.get_available_templates()
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

        # 保存日记
        file_path = ENTRIES_DIR / f"{date_str}.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = f"[{timestamp}]\n"
        if tags_str:
            full_content += f"Tags: {tags_str}\n"
        full_content += content

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        # 更新标签索引
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(',')]
            tag_data = get_tags()

            # 移除旧标签关联
            for tag, dates in tag_data.items():
                if date_str in dates:
                    dates.remove(date_str)
                    if not dates:
                        del tag_data[tag]

            # 添加新标签关联
            for tag in tags:
                if tag not in tag_data:
                    tag_data[tag] = []
                if date_str not in tag_data[tag]:
                    tag_data[tag].append(date_str)

            save_tags(tag_data)
        
        # 保存心情数据
        try:
            import utils.mood as mood_module
            mood_module.save_mood(date_str, mood_type, mood_note)
        except Exception as e:
            logger.error(f"保存心情数据失败: {e}")

        flash('日记已保存', 'success')
        return redirect(url_for('index'))

    return render_template('new.html', current_date=datetime.now().strftime(DATE_FORMAT))

@app.route('/entry/<date_str>')
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

        # 如果日期改变，需要处理文件重命名
        if new_date != date_str:
            old_path = ENTRIES_DIR / f"{date_str}.txt"
            new_path = ENTRIES_DIR / f"{new_date}.txt"
            if old_path.exists():
                old_path.rename(new_path)

        # 保存日记
        file_path = ENTRIES_DIR / f"{new_date}.txt"
        new_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = f"[{new_timestamp}]\n"
        if tags_str:
            full_content += f"Tags: {tags_str}\n"
        full_content += new_content

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        # 更新标签索引
        if tags_str:
            tags_list = [tag.strip() for tag in tags_str.split(',')]
            tag_data = get_tags()

            # 移除旧日期的标签关联
            for tag, dates in tag_data.items():
                if date_str in dates:
                    dates.remove(date_str)
                    if not dates:
                        del tag_data[tag]

            # 添加新日期的标签关联
            for tag in tags_list:
                if tag not in tag_data:
                    tag_data[tag] = []
                if new_date not in tag_data[tag]:
                    tag_data[tag].append(new_date)

            save_tags(tag_data)
        
        # 保存心情数据
        try:
            import utils.mood as mood_module
            mood_module.save_mood(new_date, mood_type, new_mood_note)
        except Exception as e:
            logger.error(f"保存心情数据失败: {e}")

        flash('日记已更新', 'success')
        return redirect(url_for('view_entry', date_str=new_date))

    return render_template('edit.html', 
                         date_str=date_str, 
                         tags=tags, 
                         content=content,
                         current_mood=current_mood,
                         mood_note=mood_note)

@app.route('/delete/<date_str>', methods=['POST'])
def delete_entry(date_str):
    # 验证日期字符串
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('index'))
    
    file_path = ENTRIES_DIR / f"{date_str}.txt"
    if file_path.exists():
        file_path.unlink()

        # 更新标签索引
        tag_data = get_tags()
        for tag, dates in tag_data.items():
            if date_str in dates:
                dates.remove(date_str)
                if not dates:
                    del tag_data[tag]
        save_tags(tag_data)

        flash('日记已删除', 'success')
    else:
        flash('未找到该日记', 'danger')
    return redirect(url_for('index'))

@app.route('/tag/<tag>')
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
                file_path = ENTRIES_DIR / f"{date_str}.txt"
                if file_path.exists():
                    entries.append(file_path)
        return render_template('tag.html', tag=tag, entries=entries)
    flash('未找到该标签', 'danger')
    return redirect(url_for('index'))

@app.route('/search', methods=['GET', 'POST'])
def search():
    """搜索日记"""
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        if not keyword:
            flash('搜索关键词不能为空', 'warning')
            return redirect(url_for('search'))
        
        # 搜索日记
        results = []
        entries = get_entries()
        
        for entry in entries:
            date_str = entry.stem
            timestamp, tags, content = get_entry_content(date_str)
            
            # 搜索内容和标签
            if keyword.lower() in content.lower() or any(keyword.lower() in tag.lower() for tag in tags):
                results.append({
                    'date_str': date_str,
                    'content': content[:100] + '...' if len(content) > 100 else content,
                    'tags': tags,
                    'size': entry.stat().st_size
                })
        
        return render_template('search.html', keyword=keyword, results=results)
    
    return render_template('search.html')

@app.route('/stats')
def stats():
    """统计页面"""
    stats_data = get_stats()
    
    # 获取标签使用频率
    tag_data = get_tags()
    tag_stats = []
    for tag, dates in tag_data.items():
        tag_stats.append({
            'tag': tag,
            'count': len(dates)
        })
    tag_stats.sort(key=lambda x: x['count'], reverse=True)
    
    # 获取每月日记数量
    monthly_stats = {}
    entries = get_entries()
    for entry in entries:
        date_str = entry.stem
        year_month = date_str[:7]  # YYYY-MM
        if year_month not in monthly_stats:
            monthly_stats[year_month] = 0
        monthly_stats[year_month] += 1
    
    # 转换为列表并排序
    monthly_stats_list = []
    for year_month, count in monthly_stats.items():
        monthly_stats_list.append({
            'month': year_month,
            'count': count
        })
    monthly_stats_list.sort(key=lambda x: x['month'])
    
    return render_template('stats.html', 
                         stats=stats_data,
                         tag_stats=tag_stats,
                         monthly_stats=monthly_stats_list)

# 图片相关路由
@app.route('/images/<path:filename>')
def serve_image(filename):
    """提供图片访问"""
    return send_from_directory('images', filename)

@app.route('/upload/image', methods=['POST'])
def upload_image():
    """上传图片"""
    if 'image' not in request.files:
        flash('请选择图片文件', 'danger')
        return redirect(request.referrer or url_for('index'))
    
    image = request.files['image']
    if image.filename == '':
        flash('请选择图片文件', 'danger')
        return redirect(request.referrer or url_for('index'))
    
    # 验证文件类型
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    if '.' not in image.filename or image.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
        flash('只支持 PNG、JPG、JPEG、GIF、WebP 格式的图片', 'danger')
        return redirect(request.referrer or url_for('index'))
    
    # 获取日期参数
    date_str = request.form.get('date', datetime.now().strftime(DATE_FORMAT))
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(request.referrer or url_for('index'))
    
    # 保存图片
    try:
        # 创建日期目录
        date_dir = IMAGES_DIR / date_str
        date_dir.mkdir(exist_ok=True)
        
        # 生成唯一文件名
        timestamp = datetime.now().strftime("%H%M%S")
        filename = f"{timestamp}_{image.filename}"
        filepath = date_dir / filename
        
        # 保存图片
        image.save(filepath)
        
        # 返回图片路径
        image_url = f"/images/{date_str}/{filename}"
        
        # 如果是 AJAX 请求，返回 JSON 响应
        if request.is_xhr or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return {'success': True, 'url': image_url}
        
        flash('图片上传成功', 'success')
        return redirect(request.referrer or url_for('index'))
    except Exception as e:
        logger.error(f"图片上传失败: {e}")
        flash('图片上传失败', 'danger')
        return redirect(request.referrer or url_for('index'))

# 导入/导出相关路由
@app.route('/import-export')
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
    except Exception as e:
        logger.error(f"导出失败: {e}")
        flash('导出失败', 'danger')
    
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

def run_production_server():
    """运行生产服务器"""
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
    host = os.environ.get('FLASK_HOST', '127.0.0.1')
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
    env = get_env()

    if env == 'production':
        run_production_server()
    else:
        run_development_server()
