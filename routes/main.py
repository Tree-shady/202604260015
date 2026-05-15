"""
主路由模块（首页、日记、日历等）
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, send_from_directory, jsonify
from pathlib import Path
from datetime import datetime, timedelta
import calendar
import logging
from typing import Optional

from utils.auth import login_required, get_current_user
from utils.models import get_session, Entry, Tag, Mood, entry_tags
from utils.validation import validate_date_str, validate_tag, sanitize_tags
from utils.greeting import get_combined_greeting, format_greeting
from utils.streak import update_streak_on_entry, get_user_streak_info, get_streak_message
from utils.favorites import get_favorites, is_favorited
from utils.config import get_config
from utils.image_utils import IMAGE_MAGIC, validate_image_magic
from utils.notification import get_notifications, get_unread_count
from utils.changelog import record_update, changelog_manager
from utils.challenges import get_user_challenge, update_daily_task_completion

logger = logging.getLogger(__name__)

main_bp = Blueprint('main', __name__)

# 配置
ENTRIES_DIR = Path("entries")
IMAGES_DIR = Path("images")
DATE_FORMAT = "%Y-%m-%d"


@main_bp.route('/')
@login_required
def index():
    """首页"""
    today = datetime.now().strftime(DATE_FORMAT)
    
    # 获取今天的日记
    entry = get_entry(today)
    
    # 获取所有心情标签
    db_session = get_session()
    moods = db_session.query(Mood).all()
    mood_list = [mood.to_dict() for mood in moods]
    db_session.close()
    
    # 获取问候语
    greeting_raw = get_combined_greeting()
    greeting = format_greeting(greeting_raw)
    
    # 获取打卡信息
    user_id = session.get('user_id')
    streak_info = get_user_streak_info(user_id)
    streak_message = get_streak_message(streak_info)
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    # 获取收藏状态
    favorited = is_favorited(user_id, today)
    
    # 获取挑战
    challenge = get_user_challenge(user_id)
    
    return render_template('index.html', 
                         entry=entry, 
                         date=today, 
                         moods=mood_list, 
                         greeting=greeting,
                         streak_info=streak_info,
                         streak_message=streak_message,
                         notifications=notifications,
                         unread_count=unread_count,
                         favorited=favorited,
                         challenge=challenge)


@main_bp.route('/entry/<date_str>')
@login_required
def entry(date_str):
    """查看日记"""
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'warning')
        return redirect(url_for('main.index'))
    
    entry = get_entry(date_str)
    if not entry:
        flash('当天没有日记', 'info')
        return redirect(url_for('main.index'))
    
    # 获取所有心情标签
    db_session = get_session()
    moods = db_session.query(Mood).all()
    mood_list = [mood.to_dict() for mood in moods]
    db_session.close()
    
    # 获取问候语
    greeting_raw = get_combined_greeting()
    greeting = format_greeting(greeting_raw)
    
    # 获取打卡信息
    user_id = session.get('user_id')
    streak_info = get_user_streak_info(user_id)
    streak_message = get_streak_message(streak_info)
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    # 获取收藏状态
    favorited = is_favorited(user_id, date_str)
    
    # 获取挑战
    challenge = get_user_challenge(user_id)
    
    return render_template('index.html', 
                         entry=entry, 
                         date=date_str, 
                         moods=mood_list,
                         greeting=greeting,
                         streak_info=streak_info,
                         streak_message=streak_message,
                         notifications=notifications,
                         unread_count=unread_count,
                         favorited=favorited,
                         challenge=challenge)


@main_bp.route('/save', methods=['POST'])
@login_required
def save():
    """保存日记"""
    date_str = request.form.get('date', datetime.now().strftime(DATE_FORMAT))
    content = request.form.get('content', '')
    title = request.form.get('title', '')
    tags_str = request.form.get('tags', '')
    mood_id = request.form.get('mood', type=int)
    weather = request.form.get('weather', '')
    location = request.form.get('location', '')
    
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'warning')
        return redirect(url_for('main.index'))
    
    # 获取当前用户
    user_id = session.get('user_id')
    user = get_current_user()
    storage = user.storage if user else 'local'
    
    tags = sanitize_tags(tags_str)
    
    try:
        save_entry(date_str, content, title, tags, mood_id, weather, location, user_id, storage)
        flash('日记保存成功！', 'success')
        
        # 更新打卡
        update_streak_on_entry(user_id, date_str)
        
        # 更新每日任务完成情况
        update_daily_task_completion(user_id, True)
        
        # 检查是否有版本更新
        try:
            latest_info = changelog_manager.get_version()
            current_info = get_config()
            
            if (latest_info.get('version') != current_info.get('version') or 
                latest_info.get('build_number') > current_info.get('build_number', 0)):
                record_update(current_info.get('version'), latest_info.get('version'))
        except Exception:
            pass
            
    except Exception as e:
        logger.error(f"Save error: {e}")
        flash(f'保存失败：{str(e)}', 'danger')
    
    return redirect(url_for('main.entry', date_str=date_str))


@main_bp.route('/delete/<date_str>')
@login_required
def delete(date_str):
    """删除日记"""
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'warning')
        return redirect(url_for('main.index'))
    
    try:
        delete_entry(date_str)
        flash('日记已删除', 'success')
    except Exception as e:
        logger.error(f"Delete error: {e}")
        flash('删除失败', 'danger')
    
    return redirect(url_for('main.index'))


@main_bp.route('/calendar')
@login_required
def calendar_view():
    """日历视图"""
    # 获取查询参数中的年月
    year = request.args.get('year', type=int)
    month = request.args.get('month', type=int)
    
    now = datetime.now()
    if not year:
        year = now.year
    if not month:
        month = now.month
    
    # 验证年月
    try:
        # 尝试创建日期来验证
        datetime(year, month, 1)
    except (ValueError, TypeError):
        flash('无效的日期', 'warning')
        return redirect(url_for('main.calendar_view'))
    
    # 生成日历
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    
    # 获取该月有日记的日期
    db_session = get_session()
    user_id = session.get('user_id')
    entries = db_session.query(Entry).filter(
        Entry.user_id == user_id,
        Entry.date >= datetime(year, month, 1).date(),
        Entry.date <= datetime(year, month, calendar.monthrange(year, month)[1]).date()
    ).all()
    entry_dates = set(entry.date.strftime(DATE_FORMAT) for entry in entries)
    db_session.close()
    
    # 获取相邻月份
    prev_month = month - 1 if month > 1 else 12
    prev_year = year - 1 if month == 1 else year
    next_month = month + 1 if month < 12 else 1
    next_year = year + 1 if month == 12 else year
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    return render_template('calendar.html', 
                         year=year, 
                         month=month, 
                         month_name=month_name,
                         cal=cal, 
                         entry_dates=entry_dates,
                         prev_month=prev_month,
                         prev_year=prev_year,
                         next_month=next_month,
                         next_year=next_year,
                         notifications=notifications,
                         unread_count=unread_count)


@main_bp.route('/search')
@login_required
def search():
    """搜索日记"""
    query = request.args.get('q', '')
    tag_filter = request.args.get('tag', '')
    mood_filter = request.args.get('mood', type=int)
    
    results = []
    if query or tag_filter or mood_filter:
        results = search_entries(query, tag_filter, mood_filter)
    
    # 获取所有标签
    db_session = get_session()
    tags = db_session.query(Tag).order_by(Tag.name).all()
    moods = db_session.query(Mood).all()
    db_session.close()
    
    # 获取通知
    notifications = get_notifications(limit=5)
    unread_count = get_unread_count()
    
    return render_template('search.html', 
                         query=query, 
                         tag_filter=tag_filter,
                         mood_filter=mood_filter,
                         results=results, 
                         tags=tags, 
                         moods=moods,
                         notifications=notifications,
                         unread_count=unread_count)


@main_bp.route('/images/<filename>')
@login_required
def serve_image(filename):
    """提供图片"""
    return send_from_directory(IMAGES_DIR, filename)


def get_entry(date_str: str) -> Optional[Entry]:
    """获取日记"""
    try:
        date = datetime.strptime(date_str, DATE_FORMAT).date()
        user_id = session.get('user_id')
        db_session = get_session()
        entry = db_session.query(Entry).filter_by(date=date, user_id=user_id).first()
        db_session.close()
        return entry
    except Exception as e:
        logger.error(f"Error getting entry: {e}")
        return None


def save_entry(date_str: str, content: str, title: str, tags: list, mood_id: Optional[int], 
               weather: str, location: str, user_id: int, storage: str) -> None:
    """保存日记"""
    date = datetime.strptime(date_str, DATE_FORMAT).date()
    
    db_session = get_session()
    
    # 检查是否已存在
    entry = db_session.query(Entry).filter_by(date=date, user_id=user_id).first()
    
    if not entry:
        # 新建
        entry = Entry(
            date=date,
            title=title,
            content=content,
            weather=weather,
            location=location,
            user_id=user_id,
            storage=storage
        )
        db_session.add(entry)
        db_session.flush()  # 获取 ID
    else:
        # 更新
        entry.title = title
        entry.content = content
        entry.weather = weather
        entry.location = location
        entry.updated_at = datetime.now()
    
    # 处理心情
    if mood_id:
        entry.mood_id = mood_id
    else:
        entry.mood_id = None
    
    # 处理标签
    entry.tags = []
    for tag_name in tags:
        tag = db_session.query(Tag).filter_by(name=tag_name).first()
        if not tag:
            tag = Tag(name=tag_name)
            db_session.add(tag)
        entry.tags.append(tag)
    
    db_session.commit()
    db_session.close()


def delete_entry(date_str: str) -> None:
    """删除日记"""
    date = datetime.strptime(date_str, DATE_FORMAT).date()
    user_id = session.get('user_id')
    
    db_session = get_session()
    entry = db_session.query(Entry).filter_by(date=date, user_id=user_id).first()
    if entry:
        db_session.delete(entry)
        db_session.commit()
    db_session.close()


def search_entries(query: str, tag_filter: str, mood_filter: Optional[int]) -> list:
    """搜索日记"""
    user_id = session.get('user_id')
    db_session = get_session()
    
    q = db_session.query(Entry).filter_by(user_id=user_id)
    
    if query:
        search_str = f'%{query}%'
        q = q.filter(
            (Entry.title.like(search_str)) | 
            (Entry.content.like(search_str))
        )
    
    if tag_filter:
        tag = db_session.query(Tag).filter_by(name=tag_filter).first()
        if tag:
            q = q.filter(Entry.tags.any(id=tag.id))
    
    if mood_filter:
        q = q.filter_by(mood_id=mood_filter)
    
    results = q.order_by(Entry.date.desc()).all()
    db_session.close()
    
    return results
