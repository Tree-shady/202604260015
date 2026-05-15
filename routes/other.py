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
from utils.challenges import get_user_challenge, update_challenge_settings, update_daily_task_completion
from utils.notification import get_notifications, get_unread_count
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
    user_id = session.get('user_id')
    db_session = get_session()
    
    # 统计信息
    total_entries = db_session.query(Entry).filter_by(user_id=user_id).count()
    this_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_entries = db_session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.created_at >= this_month
    ).count()
    
    # 获取心情统计
    mood_stats = {}
    entries = db_session.query(Entry).filter_by(user_id=user_id).all()
    for entry in entries:
        if entry.mood:
            mood_name = entry.mood.name
            mood_stats[mood_name] = mood_stats.get(mood_name, 0) + 1
    
    db_session.close()
    
    # 习惯分析
    habit_analysis = get_habit_analysis(user_id)
    streak_chart = get_streak_chart_data(user_id)
    weekly_heatmap = get_weekly_heatmap(user_id)
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    return render_template('stats.html',
                         total_entries=total_entries,
                         monthly_entries=monthly_entries,
                         mood_stats=mood_stats,
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
    
    return render_template('settings.html', 
                         config=config,
                         user=user,
                         notifications=notifications,
                         unread_count=unread_count)


@other_bp.route('/settings', methods=['POST'])
@login_required
def save_settings():
    """保存设置"""
    config = get_config()
    
    # 更新设置
    config['notifications'] = {
        'reminder_enabled': request.form.get('reminder_enabled') == 'on',
        'reminder_time': request.form.get('reminder_time', '21:00')
    }
    
    # 如果有统计相关设置
    config['stats'] = {
        'show_mood_chart': request.form.get('show_mood_chart') == 'on',
        'show_streak_chart': request.form.get('show_streak_chart') == 'on'
    }
    
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
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    return render_template('yearly_review.html',
                         review=review,
                         year=year,
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
        flash('没有选择文件！', 'danger')
        return redirect(url_for('main.index'))
    
    file = request.files['image']
    if file.filename == '':
        flash('没有选择文件！', 'danger')
        return redirect(url_for('main.index'))
    
    if file and allowed_file(file.filename):
        # 生成唯一文件名
        filename = generate_unique_filename(file.filename)
        filepath = IMAGES_DIR / filename
        
        # 保存文件
        file.save(filepath)
        
        # 验证文件是否是真正的图片
        if not validate_image_magic(filepath):
            os.remove(filepath)
            flash('上传的文件不是有效的图片！', 'danger')
            return redirect(url_for('main.index'))
        
        # 返回图片URL
        flash('图片上传成功！', 'success')
        return redirect(url_for('main.index'))
    
    flash('不支持的文件类型！', 'danger')
    return redirect(url_for('main.index'))


@other_bp.route('/export', methods=['POST'])
@login_required
def export_data():
    """导出数据"""
    format = request.form.get('format', 'json')
    date_from = request.form.get('date_from', '')
    date_to = request.form.get('date_to', '')
    
    user_id = session.get('user_id')
    db_session = get_session()
    
    # 构建查询
    query = db_session.query(Entry).filter_by(user_id=user_id)
    
    if date_from:
        query = query.filter(Entry.date >= datetime.strptime(date_from, DATE_FORMAT).date())
    if date_to:
        query = query.filter(Entry.date <= datetime.strptime(date_to, DATE_FORMAT).date())
    
    entries = query.order_by(Entry.date).all()
    db_session.close()
    
    if format == 'json':
        # 导出为JSON
        data = []
        for entry in entries:
            data.append({
                'date': entry.date.strftime(DATE_FORMAT),
                'title': entry.title,
                'content': entry.content,
                'mood': entry.mood.name if entry.mood else None,
                'weather': entry.weather,
                'location': entry.location,
                'tags': [tag.name for tag in entry.tags],
                'created_at': entry.created_at.isoformat() if entry.created_at else None,
                'updated_at': entry.updated_at.isoformat() if entry.updated_at else None
            })
        
        # 生成下载文件
        filename = f'diary_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json'
        filepath = Path("data") / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        flash(f'已导出 {len(entries)} 条日记！', 'success')
        return send_from_directory("data", filename, as_attachment=True)
    
    flash('导出失败！', 'danger')
    return redirect(url_for('main.index'))


@other_bp.route('/import', methods=['POST'])
@login_required
def import_data():
    """导入数据"""
    if 'file' not in request.files:
        flash('没有选择文件！', 'danger')
        return redirect(url_for('other.settings'))
    
    file = request.files['file']
    if file.filename == '':
        flash('没有选择文件！', 'danger')
        return redirect(url_for('other.settings'))
    
    if file and file.filename.endswith('.json'):
        try:
            data = json.load(file)
            user_id = session.get('user_id')
            
            db_session = get_session()
            imported_count = 0
            
            for item in data:
                try:
                    date_str = item.get('date')
                    date = datetime.strptime(date_str, DATE_FORMAT).date()
                    
                    # 检查是否已存在
                    existing = db_session.query(Entry).filter_by(
                        date=date,
                        user_id=user_id
                    ).first()
                    
                    if existing:
                        continue
                    
                    # 创建新条目
                    entry = Entry(
                        date=date,
                        title=item.get('title', ''),
                        content=item.get('content', ''),
                        weather=item.get('weather', ''),
                        location=item.get('location', ''),
                        user_id=user_id
                    )
                    db_session.add(entry)
                    imported_count += 1
                    
                except Exception as e:
                    logger.warning(f"Failed to import entry: {e}")
                    continue
            
            db_session.commit()
            db_session.close()
            
            flash(f'成功导入 {imported_count} 条日记！', 'success')
            
        except Exception as e:
            logger.error(f"Import error: {e}")
            flash('导入失败：' + str(e), 'danger')
    else:
        flash('请上传JSON文件！', 'danger')
    
    return redirect(url_for('other.settings'))


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
