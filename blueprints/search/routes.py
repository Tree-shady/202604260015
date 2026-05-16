from flask import render_template, request, session
from utils.models import get_session, Entry, Tag, Mood
from utils.auth import login_required
from . import search_bp
import logging

logger = logging.getLogger(__name__)


@search_bp.route('/', methods=['GET', 'POST'])
@login_required
def search():
    """搜索日记"""
    db_session = get_session()
    current_user_id = session.get('user_id')
    
    all_tags = [t.name for t in db_session.query(Tag).all()]
    
    if request.method == 'POST':
        keyword = request.form.get('keyword', '').strip()
        start_date = request.form.get('start_date', '').strip()
        end_date = request.form.get('end_date', '').strip()
        selected_moods = request.form.getlist('moods')
        selected_tag = request.form.get('tag', '').strip()
        
        query = db_session.query(Entry).filter_by(user_id=current_user_id)
        
        if start_date:
            query = query.filter(Entry.date_str >= start_date)
        if end_date:
            query = query.filter(Entry.date_str <= end_date)
        
        if keyword:
            query = query.filter(Entry.content.ilike(f'%{keyword}%'))
        
        if selected_tag:
            tag_obj = db_session.query(Tag).filter_by(name=selected_tag).first()
            if tag_obj:
                query = query.filter(Entry.tags.contains(tag_obj))
        
        if selected_moods:
            query = query.join(Entry.mood).filter(Mood.mood_type.in_(selected_moods))
        
        entries = query.order_by(Entry.date_str.desc()).all()
        
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
