"""
其他功能路由模块（收藏、统计、设置等）
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory
from pathlib import Path
import os
import logging
import uuid
import json

from utils.auth import login_required, get_current_user
from utils.models import get_session, Entry
from utils.config import get_config, save_config
from utils.image_utils import validate_image_magic, allowed_file, generate_unique_filename
from utils.yearly_review import get_yearly_review
from utils.habits import get_habit_analysis, get_streak_chart_data, get_weekly_heatmap
from utils.favorites import get_favorites
from utils.challenges import get_user_challenge, update_challenge_settings, update_daily_task_completion, start_challenge, get_all_challenges_status, abandon_challenge
from utils.notification import get_notifications, get_unread_count, add_notification
from utils.settings import set_user_setting, get_user_setting
from datetime import datetime

logger = logging.getLogger(__name__)

other_bp = Blueprint('other', __name__)

# 配置常量
ENTRIES_DIR = Path("entries")
IMAGES_DIR = Path("images")
DATE_FORMAT = "%Y-%m-%d"


@other_bp.route('/favorites')
@login_required
def favorites():
    """收藏列表"""
    user_id = session.get('user_id')
    favorites_list = get_favorites(user_id)
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    return render_template('favorites.html', 
                         favorites=favorites_list,
                         notifications=notifications,
                         unread_count=unread_count)


@other_bp.route('/stats')
@login_required
def stats():
    """统计页面"""
    from sqlalchemy import func, extract
    user_id = session.get('user_id')
    db_session = get_session()
    
    # 使用 SQL 聚合查询获取基本统计
    basic_stats = db_session.query(
        func.count(Entry.id).label('total_entries'),
        func.sum(func.length(Entry.content)).label('total_chars')
    ).filter(Entry.user_id == user_id).first()
    
    total_entries = basic_stats.total_entries or 0
    total_chars = basic_stats.total_chars or 0
    
    # 获取用户的所有日记（用于计算字数和其他统计）
    entries = db_session.query(Entry).filter_by(user_id=user_id).all()
    total_words = sum(len(e.content.split()) for e in entries)
    
    # 标签统计 - 使用 SQL 查询优化
    from utils.models import Tag, entry_tags
    tag_stats = db_session.query(
        Tag.name,
        func.count(Entry.id).label('count')
    ).join(entry_tags, Tag.id == entry_tags.c.tag_id)\
     .join(Entry, entry_tags.c.entry_id == Entry.id)\
     .filter(Entry.user_id == user_id)\
     .group_by(Tag.id, Tag.name)\
     .order_by(func.count(Entry.id).desc())\
     .limit(10)\
     .all()
    
    tag_stats_list = [{'tag': name, 'count': count} for name, count in tag_stats]
    total_tags = len(tag_stats_list)
    
    # 按月统计 - 使用 SQL 聚合
    monthly_stats = db_session.query(
        func.substr(Entry.date_str, 1, 7).label('month'),
        func.count(Entry.id).label('count')
    ).filter(Entry.user_id == user_id)\
     .group_by(func.substr(Entry.date_str, 1, 7))\
     .order_by('month')\
     .all()
    
    monthly_stats_list = [{'month': month, 'count': count} for month, count in monthly_stats]
    
    # 心情统计 - 使用 SQL 聚合
    from utils.models import Mood
    mood_stats_query = db_session.query(
        Mood.mood_type,
        func.count(Entry.id).label('count')
    ).join(Mood, Entry.id == Mood.entry_id)\
     .filter(Entry.user_id == user_id)\
     .group_by(Mood.mood_type)\
     .all()
    
    mood_stats = {'happy': 0, 'excited': 0, 'calm': 0, 'tired': 0, 'sad': 0, 'angry': 0, 'anxious': 0, 'neutral': 0}
    for mood_type, count in mood_stats_query:
        mood_stats[mood_type] = count
    
    # 获取最近30天的心情数据
    mood_trend = []
    today = datetime.now().date()
    
    # 构建日期到日记的映射
    entries_by_date = {e.date_str: e for e in entries}
    
    mood_emoji = {'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'}
    mood_labels = {'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'}
    
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
    
    db_session.close()
    
    # 习惯分析
    habit_analysis = get_habit_analysis(user_id)
    streak_chart = get_streak_chart_data(user_id)
    weekly_heatmap = get_weekly_heatmap(user_id)
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    return render_template('stats.html',
                         stats=stats_data,
                         tag_stats=tag_stats_list,
                         monthly_stats=monthly_stats_list,
                         mood_stats=mood_stats,
                         mood_trend=mood_trend,
                         habit_analysis=habit_analysis,
                         streak_chart=streak_chart,
                         weekly_heatmap=weekly_heatmap,
                         notifications=notifications,
                         unread_count=unread_count)


@other_bp.route('/settings')
@login_required
def settings():
    """设置页面"""
    config = get_config()
    user = get_current_user()
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    # 获取远程数据库配置
    from utils.db_manager import db_manager
    remote_config = db_manager.load_config().get('remote', {})
    
    return render_template('settings.html', 
                         config=config,
                         user=user,
                         notifications=notifications,
                         unread_count=unread_count,
                         remote_config=remote_config)


@other_bp.route('/settings', methods=['POST'])
@login_required
def save_settings():
    """保存设置"""
    config = get_config()
    
    # 更新设置
    config['theme'] = request.form.get('theme', 'light')
    config['backup_enabled'] = 'backup_enabled' in request.form
    config['auto_save'] = 'auto_save' in request.form
    config['notifications'] = {
        'enabled': 'notifications_enabled' in request.form
    }
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
        if storage_location == 'remote' and not db_manager.is_remote_configured():
            flash('远程数据库尚未配置，请先配置远程数据库', 'warning')
        else:
            session['storage_type'] = storage_location
            flash(f'存储位置已设置为{"云端" if storage_location == "remote" else "本地"}，请重新登录生效', 'info')
    
    save_config(config)
    flash('设置已保存！', 'success')
    return redirect(url_for('other.settings'))


@other_bp.route('/yearly-review')
@login_required
def yearly_review():
    """年度回顾"""
    year = request.args.get('year', datetime.now().year, type=int)
    user_id = session.get('user_id')
    
    review = get_yearly_review(user_id, year)
    
    # 提供年份选择（有日记的年份）
    session_db = get_session()
    user_entries = session_db.query(Entry).filter_by(user_id=user_id).all()
    available_years = sorted(list(set([int(e.date_str[:4]) for e in user_entries])), reverse=True)
    session_db.close()
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    mood_emoji = {'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'}
    mood_labels = {'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'}
    
    return render_template('yearly_review.html',
                         review=review,
                         year=year,
                         available_years=available_years,
                         mood_emoji=mood_emoji,
                         mood_labels=mood_labels,
                         notifications=notifications,
                         unread_count=unread_count)


@other_bp.route('/reminders')
@login_required
def reminders():
    """提醒页面"""
    config = get_config()
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    return render_template('reminders.html',
                         config=config,
                         notifications=notifications,
                         unread_count=unread_count)


@other_bp.route('/reminders', methods=['POST'])
@login_required
def save_reminders():
    """保存提醒设置"""
    config = get_config()
    
    # 更新提醒设置
    config['notifications'] = {
        'reminder_enabled': request.form.get('reminder_enabled') == 'on',
        'reminder_time': request.form.get('reminder_time', '21:00'),
        'daily_reminder': request.form.get('daily_reminder') == 'on',
        'weekly_digest': request.form.get('weekly_digest') == 'on',
        'milestone_notifications': request.form.get('milestone_notifications') == 'on'
    }
    
    save_config(config)
    
    flash('提醒设置已保存！', 'success')
    return redirect(url_for('other.reminders'))


@other_bp.route('/upload/image', methods=['POST'])
@login_required
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
    from utils.validation import validate_date_str
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
        
        # 验证文件是否是真正的图片 (Magic Number检查)
        if not validate_image_magic(filepath):
            os.remove(filepath)
            return {'success': False, 'message': '文件不是有效的图片'}, 400
        
        # 返回图片URL
        image_url = f"/images/{date_str}/{filename}"
        return {'success': True, 'url': image_url}
        
    except Exception as e:
        logger.error(f"图片上传失败: {e}")
        return {'success': False, 'message': '图片上传失败'}, 500


@other_bp.route('/import-export')
@login_required
def import_export():
    """导入/导出页面"""
    return render_template('import_export.html')


@other_bp.route('/export', methods=['POST'])
@login_required
def export_data():
    """导出数据"""
    export_format = request.form.get('format', 'json')
    date_from = request.form.get('date_from', '')
    date_to = request.form.get('date_to', '')
    
    try:
        import utils.import_export as ie
        
        if export_format == 'json':
            file_path = ie.export_to_json(date_from, date_to)
        elif export_format == 'csv':
            file_path = ie.export_to_csv(date_from, date_to)
        elif export_format == 'markdown':
            file_path = ie.export_to_markdown(date_from, date_to)
        elif export_format == 'zip':
            file_path = ie.export_to_zip(date_from, date_to)
        else:
            flash('无效的导出格式', 'danger')
            return redirect(url_for('other.import_export'))
        
        flash(f'导出成功，文件保存至: {file_path}', 'success')
        
        # 添加通知
        try:
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
            add_notification(
                message=f'导出失败：{str(e)}',
                level='error',
                title='导出失败'
            )
        except Exception:
            pass
    
    return redirect(url_for('other.import_export'))


@other_bp.route('/import', methods=['POST'])
@login_required
def import_data():
    """导入数据"""
    if 'file' not in request.files:
        flash('没有选择文件！', 'danger')
        return redirect(url_for('other.import_export'))
    
    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件！', 'danger')
        return redirect(url_for('other.import_export'))
    
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
            return redirect(url_for('other.import_export'))
        
        # 清理临时文件
        os.unlink(temp_path)
        
        flash(f'导入成功: {result["success"]} 成功, {result["failed"]} 失败', 'success')
    except Exception as e:
        logger.error(f"导入失败: {e}")
        flash('导入失败', 'danger')
    
    return redirect(url_for('other.import_export'))


@other_bp.route('/challenges')
@login_required
def challenges():
    """写作挑战页面"""
    user_id = session.get('user_id')
    challenge_status = get_all_challenges_status(user_id)
    
    return render_template('challenges.html',
                         challenge_status=challenge_status)


@other_bp.route('/challenges/start', methods=['POST'])
@login_required
def challenges_start():
    """开始挑战"""
    user_id = session.get('user_id')
    challenge_id = request.form.get('challenge_id')
    
    result = start_challenge(user_id, challenge_id)
    
    if result:
        if result['has_active']:
            flash('你已经有进行中的挑战了！', 'warning')
        else:
            flash(f"开始{result['challenge']['name']}！加油！💪", 'success')
    else:
        flash('挑战不存在', 'danger')
    
    return redirect(url_for('other.challenges'))


@other_bp.route('/challenges/abandon', methods=['POST'])
@login_required
def challenges_abandon():
    """放弃挑战"""
    user_id = session.get('user_id')
    abandon_challenge(user_id)
    flash('已放弃当前挑战', 'info')
    return redirect(url_for('other.challenges'))


@other_bp.route('/challenge')
@login_required
def challenge():
    """挑战页面"""
    user_id = session.get('user_id')
    challenge = get_user_challenge(user_id)
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    return render_template('challenge.html',
                         challenge=challenge,
                         notifications=notifications,
                         unread_count=unread_count)


@other_bp.route('/challenge/settings', methods=['POST'])
@login_required
def challenge_settings():
    """挑战设置"""
    user_id = session.get('user_id')
    
    enabled = request.form.get('enabled') == 'on'
    target_days = request.form.get('target_days', 30, type=int)
    notification_enabled = request.form.get('notification_enabled') == 'on'
    
    update_challenge_settings(user_id, enabled, target_days, notification_enabled)
    
    flash('挑战设置已保存！', 'success')
    return redirect(url_for('other.challenge'))


@other_bp.route('/challenge/daily', methods=['POST'])
@login_required
def daily_task():
    """每日任务完成"""
    user_id = session.get('user_id')
    completed = request.form.get('completed') == 'on'
    
    success = update_daily_task_completion(user_id, completed)
    
    if success:
        flash('任务状态已更新！', 'success')
    else:
        flash('更新失败！', 'danger')
    
    return redirect(url_for('other.challenge'))


@other_bp.route('/reminder', methods=['GET', 'POST'])
@login_required
def reminder():
    """日记提醒设置"""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        reminder_time = request.form.get('reminder_time', '21:00')
        enabled = request.form.get('enabled', 'off') == 'on'
        
        # 保存到用户设置
        set_user_setting(user_id, 'reminder_enabled', enabled)
        set_user_setting(user_id, 'reminder_time', reminder_time)
        
        flash(f'提醒设置已更新', 'success')
        return redirect(url_for('other.reminder'))
    
    enabled = get_user_setting(user_id, 'reminder_enabled', False)
    reminder_time = get_user_setting(user_id, 'reminder_time', '21:00')
    
    return render_template('reminder.html', 
                         enabled=enabled,
                         reminder_time=reminder_time)


# 添加必要的导入
from datetime import timedelta

