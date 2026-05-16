from flask import render_template, request, redirect, url_for, flash, session, send_from_directory
from datetime import datetime
from pathlib import Path
from utils.models import get_session, Entry, Tag, Mood, entry_tags
from utils.validation import validate_date_str, validate_tag, sanitize_tags
from utils.auth import login_required
from utils.streak import (
    update_streak_on_entry,
    get_user_streak_info,
    get_streak_message,
    get_streak_reward
)
from utils.yearly_review import get_yearly_review
from utils.habits import (
    get_writing_heatmap,
    get_best_writing_time,
    get_writing_streak_analysis,
    get_monthly_completion,
    get_year_summary
)
from utils.memories import get_same_day_last_years, get_milestone_entries
from utils.challenges import (
    start_challenge,
    abandon_challenge,
    get_all_challenges_status
)
from utils.notification import add_notification
from utils.storage import IMAGES_DIR
from utils.config import DATE_FORMAT
from sqlalchemy.orm import joinedload
import logging
import uuid
import os

logger = logging.getLogger(__name__)
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


def get_calendar_data(year, month):
    """获取日历数据"""
    from calendar import monthrange, weekday

    days_in_month = monthrange(year, month)[1]
    first_day_weekday = weekday(year, month, 1)
    first_day_weekday = (first_day_weekday + 1) % 7

    calendar_days = []

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

    today = datetime.now()
    current_year, current_month, current_day = today.year, today.month, today.day

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


def get_entry_content(date_str):
    """获取日记内容"""
    db_session = get_session()
    entry = db_session.query(Entry).filter_by(date_str=date_str).first()
    if entry:
        timestamp = f"[{entry.timestamp.strftime('%Y-%m-%d %H:%M:%S')}]"
        tags = [tag.name for tag in entry.tags]
        content = entry.content
        return timestamp, tags, content
    return None, [], ""


@diary_bp.route('/')
@diary_bp.route('/<int:year>/<int:month>')
@login_required
def index(year=None, month=None):
    """日记首页"""
    if not year or not month:
        today = datetime.now()
        year, month = today.year, today.month

    db_session = get_session()
    current_user_id = session.get('user_id')
    
    entries = db_session.query(Entry).options(
        joinedload(Entry.tags),
        joinedload(Entry.mood)
    ).filter_by(user_id=current_user_id).order_by(Entry.date_str.desc()).limit(5).all()
    
    from flask import current_app
    tag_data = current_app.cache.get('tags') or {}
    calendar_data = get_calendar_data(year, month)

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

    mood_stats = {}
    for entry in entries:
        if entry.mood:
            mt = entry.mood.mood_type
            mood_stats[mt] = mood_stats.get(mt, 0) + 1
    
    from utils.greeting import get_combined_greeting
    greeting_data = get_combined_greeting()
    
    streak_info = get_user_streak_info(current_user_id)
    streak_message = get_streak_message(streak_info['current_streak'], streak_info['longest_streak'])
    streak_badges = get_streak_reward(streak_info['current_streak'])

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
                         mood_stats=mood_stats,
                         mood_emoji={'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'},
                         mood_labels={'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'},
                         greeting_data=greeting_data,
                         streak_info=streak_info,
                         streak_message=streak_message,
                         streak_badges=streak_badges,
                         memories_data=memories_data,
                         milestone_data=milestone_data)


@diary_bp.route('/new', methods=['GET', 'POST'])
@login_required
def new_entry():
    """新建日记"""
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
            return redirect(url_for('diary.new_entry'))

        try:
            datetime.strptime(date_str, DATE_FORMAT)
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式', 'danger')
            return redirect(url_for('diary.new_entry'))

        if template_id:
            import utils.templates as template_module
            valid_templates = template_module.get_all_templates()
            if template_id not in valid_templates:
                flash('无效的模板ID', 'danger')
                return redirect(url_for('diary.new_entry'))

        import utils.mood as mood_module
        if mood_type not in mood_module.MOOD_TYPES:
            flash('无效的心情类型', 'danger')
            return redirect(url_for('diary.new_entry'))

        if len(mood_note) > 200:
            flash('心情备注长度不能超过200个字符', 'danger')
            return redirect(url_for('diary.new_entry'))

        if template_id:
            try:
                content = template_module.render_template(template_id, date_str)
            except Exception as e:
                logger.error(f"模板渲染失败: {e}")

        db_session = get_session()
        current_user_id = session.get('user_id')
        
        logger.debug(f"准备保存日记 - 用户ID: {current_user_id}")

        existing_entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=date_str).first()
        if existing_entry:
            logger.debug(f"该日期的日记已存在: {date_str}")
            flash('该日期的日记已存在', 'danger')
            return redirect(url_for('diary.new_entry'))

        entry = Entry(
            user_id=current_user_id,
            date_str=date_str,
            content=content,
            timestamp=datetime.now()
        )
        db_session.add(entry)
        db_session.flush()

        if tags_str:
            tags = sanitize_tags(tags_str)
            for tag_name in tags:
                if tag_name and validate_tag(tag_name):
                    tag = db_session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db_session.add(tag)
                    entry.tags.append(tag)

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

        streak_info = None
        try:
            streak_info = update_streak_on_entry(current_user_id, date_str)
            logger.debug(f"打卡统计更新: {streak_info}")
        except Exception as e:
            logger.error(f"更新打卡统计失败: {e}")

        try:
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
        return redirect(url_for('diary.index'))

    return render_template('new.html', current_date=datetime.now().strftime(DATE_FORMAT))


@diary_bp.route('/entry/<date_str>')
@login_required
def view_entry(date_str):
    """查看日记"""
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('diary.index'))
    
    timestamp, tags, content = get_entry_content(date_str)
    if content:
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
    return redirect(url_for('diary.index'))


@diary_bp.route('/edit/<date_str>', methods=['GET', 'POST'])
@login_required
def edit_entry(date_str):
    """编辑日记"""
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('diary.index'))
    
    timestamp, tags, content = get_entry_content(date_str)
    if not content:
        flash('未找到该日记', 'danger')
        return redirect(url_for('diary.index'))

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
            return redirect(url_for('diary.edit_entry', date_str=date_str))

        try:
            datetime.strptime(new_date, DATE_FORMAT)
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式', 'danger')
            return redirect(url_for('diary.edit_entry', date_str=date_str))

        import utils.mood as mood_module
        if mood_type not in mood_module.MOOD_TYPES:
            flash('无效的心情类型', 'danger')
            return redirect(url_for('diary.edit_entry', date_str=date_str))

        if len(new_mood_note) > 200:
            flash('心情备注长度不能超过200个字符', 'danger')
            return redirect(url_for('diary.edit_entry', date_str=date_str))

        db_session = get_session()
        current_user_id = session.get('user_id')

        entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=date_str).first()
        if not entry:
            flash('未找到该日记', 'danger')
            return redirect(url_for('diary.index'))

        if new_date != date_str:
            existing_entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=new_date).first()
            if existing_entry:
                flash('新日期的日记已存在', 'danger')
                return redirect(url_for('diary.edit_entry', date_str=date_str))
            entry.date_str = new_date

        entry.content = new_content
        entry.timestamp = datetime.now()

        entry.tags = []
        if tags_str:
            tags_list = sanitize_tags(tags_str)
            for tag_name in tags_list:
                if tag_name and validate_tag(tag_name):
                    tag = db_session.query(Tag).filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db_session.add(tag)
                    entry.tags.append(tag)

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

        try:
            add_notification(
                message=f'日记已更新：{new_date}',
                level='success',
                title='日记更新成功'
            )
        except Exception as e:
            logger.error(f"添加通知失败: {e}")

        flash('日记已更新', 'success')
        return redirect(url_for('diary.view_entry', date_str=new_date))

    return render_template('edit.html', 
                         date_str=date_str, 
                         tags=tags, 
                         content=content,
                         current_mood=current_mood,
                         mood_note=mood_note)


@diary_bp.route('/delete/<date_str>', methods=['GET'])
@login_required
def delete_entry_confirm(date_str):
    """显示删除确认页面"""
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('diary.index'))
    
    db_session = get_session()
    current_user_id = session.get('user_id')
    entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=date_str).first()
    
    if not entry:
        flash('未找到该日记', 'danger')
        return redirect(url_for('diary.index'))
    
    timestamp = entry.timestamp.strftime('%Y-%m-%d %H:%M') if entry.timestamp else ''
    content = entry.content[:200] if entry.content else ''
    
    mood_info = None
    mood_note = ''
    if entry.mood:
        mood_info = entry.mood.mood_type
    
    tags = [t.name for t in entry.tags]
    
    mood_emoji = {'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'}
    mood_label = {'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'}
    
    return render_template('confirm_delete.html', 
                         date_str=date_str,
                         timestamp=timestamp,
                         content=content,
                         mood_info={'emoji': mood_emoji.get(mood_info, '😐'), 'label': mood_label.get(mood_info, '一般')},
                         mood_note=mood_note,
                         tags=tags)


@diary_bp.route('/delete/<date_str>', methods=['POST'])
@login_required
def delete_entry(date_str):
    """执行删除操作"""
    if not validate_date_str(date_str):
        flash('无效的日期格式', 'danger')
        return redirect(url_for('diary.index'))
    
    db_session = get_session()
    current_user_id = session.get('user_id')
    entry = db_session.query(Entry).filter_by(user_id=current_user_id, date_str=date_str).first()
    if entry:
        db_session.delete(entry)
        db_session.commit()
        flash('日记已删除', 'success')
    else:
        flash('未找到该日记', 'danger')
    return redirect(url_for('diary.index'))


@diary_bp.route('/tag/<tag>')
@login_required
def view_tag(tag):
    """查看标签"""
    if not validate_tag(tag):
        flash('无效的标签名称', 'danger')
        return redirect(url_for('diary.index'))
    
    from flask import current_app
    tag_data = current_app.cache.get('tags') or {}
    
    if tag in tag_data:
        dates = tag_data[tag]
        entries = []
        for date_str in dates:
            if validate_date_str(date_str):
                class MockPath:
                    def __init__(self, date_str):
                        self.stem = date_str
                        self.stat = lambda: type('obj', (object,), {'st_size': 0})
                entries.append(MockPath(date_str))
        return render_template('tag.html', tag=tag, entries=entries)
    flash('未找到该标签', 'danger')
    return redirect(url_for('diary.index'))


@diary_bp.route('/stats')
@login_required
def stats():
    """统计页面"""
    db_session = get_session()
    current_user_id = session.get('user_id')
    
    entries = db_session.query(Entry).options(
        joinedload(Entry.tags),
        joinedload(Entry.mood)
    ).filter_by(user_id=current_user_id).all()
    total_entries = len(entries)
    
    total_chars = sum(len(e.content) for e in entries)
    total_words = sum(len(e.content.split()) for e in entries)
    
    tag_stats = {}
    for entry in entries:
        for tag in entry.tags:
            tag_stats[tag.name] = tag_stats.get(tag.name, 0) + 1
    tag_stats_list = [{'tag': k, 'count': v} for k, v in sorted(
        tag_stats.items(), key=lambda x: x[1], reverse=True
    )][:10]
    total_tags = len(tag_stats_list)
    
    monthly_stats_dict = {}
    for entry in entries:
        month = entry.date_str[:7]
        if month not in monthly_stats_dict:
            monthly_stats_dict[month] = 0
        monthly_stats_dict[month] += 1
    monthly_stats_list = [{'month': m, 'count': c} for m, c in sorted(monthly_stats_dict.items())]
    
    mood_stats = {'happy': 0, 'excited': 0, 'calm': 0, 'tired': 0, 'sad': 0, 'angry': 0, 'anxious': 0, 'neutral': 0}
    for entry in entries:
        if entry.mood:
            mood_stats[entry.mood.mood_type] = mood_stats.get(entry.mood.mood_type, 0) + 1
    
    mood_labels = {'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'}
    mood_emoji = {'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'}
    
    mood_trend = []
    from datetime import timedelta
    today = datetime.now().date()
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


@diary_bp.route('/yearly-review', methods=['GET'])
@login_required
def yearly_review():
    """年度回顾页面"""
    current_user_id = session.get('user_id')
    year = request.args.get('year', datetime.now().year, type=int)
    
    review_data = get_yearly_review(current_user_id, year)
    
    session_db = get_session()
    user_entries = session_db.query(Entry).filter_by(user_id=current_user_id).all()
    available_years = sorted(list(set([int(e.date_str[:4]) for e in user_entries])), reverse=True)
    
    return render_template('yearly_review.html', 
                         review_data=review_data,
                         available_years=available_years,
                         selected_year=year,
                         mood_emoji={'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴', 'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'},
                         mood_labels={'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫', 'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'})


@diary_bp.route('/habits')
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


@diary_bp.route('/challenges')
@login_required
def challenges():
    """写作挑战页面"""
    current_user_id = session.get('user_id')
    challenge_status = get_all_challenges_status(current_user_id)
    return render_template('challenges.html', challenge_status=challenge_status)


@diary_bp.route('/challenges/start', methods=['POST'])
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
    
    return redirect(url_for('diary.challenges'))


@diary_bp.route('/challenges/abandon', methods=['POST'])
@login_required
def challenges_abandon():
    """放弃挑战"""
    current_user_id = session.get('user_id')
    abandon_challenge(current_user_id)
    flash('已放弃当前挑战', 'info')
    return redirect(url_for('diary.challenges'))


@diary_bp.route('/reminder', methods=['GET', 'POST'])
@login_required
def reminder():
    """日记提醒设置"""
    current_user_id = session.get('user_id')
    
    if request.method == 'POST':
        reminder_time = request.form.get('reminder_time', '21:00')
        enabled = request.form.get('enabled', 'off') == 'on'
        
        from utils.settings import set_user_setting
        set_user_setting(current_user_id, 'reminder_enabled', enabled)
        set_user_setting(current_user_id, 'reminder_time', reminder_time)
        
        flash(f'提醒设置已更新', 'success')
        return redirect(url_for('diary.reminder'))
    
    from utils.settings import get_user_setting
    enabled = get_user_setting(current_user_id, 'reminder_enabled', False)
    reminder_time = get_user_setting(current_user_id, 'reminder_time', '21:00')
    
    return render_template('reminder.html', 
                         enabled=enabled,
                         reminder_time=reminder_time)


@diary_bp.route('/upload/image', methods=['POST'])
def upload_image():
    """上传图片"""
    if 'image' not in request.files:
        return {'success': False, 'message': '请选择图片文件'}, 400
    
    image = request.files['image']
    if image.filename == '':
        return {'success': False, 'message': '请选择图片文件'}, 400
    
    allowed_extensions = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    ext = image.filename.rsplit('.', 1)[-1].lower() if '.' in image.filename else ''
    if ext not in allowed_extensions:
        return {'success': False, 'message': '只支持 PNG、JPG、JPEG、GIF、WebP 格式'}, 400
    
    date_str = request.form.get('date', datetime.now().strftime(DATE_FORMAT))
    if not validate_date_str(date_str):
        return {'success': False, 'message': '无效的日期格式'}, 400
    
    try:
        date_dir = IMAGES_DIR / date_str
        date_dir.mkdir(exist_ok=True)
        
        ext = image.filename.rsplit('.', 1)[-1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = date_dir / filename
        
        image.save(filepath)
        
        if not validate_image_magic(filepath):
            os.remove(filepath)
            return {'success': False, 'message': '文件不是有效的图片'}, 400
        
        image_url = f"/images/{date_str}/{filename}"
        return {'success': True, 'url': image_url}
        
    except Exception as e:
        logger.error(f"图片上传失败: {e}")
        return {'success': False, 'message': '图片上传失败'}, 500


@diary_bp.route('/images/<path:filename>')
def serve_image(filename):
    """提供图片访问"""
    return send_from_directory(IMAGES_DIR, filename)
