"""
API 路由模块
"""
from flask import Blueprint, request, jsonify, session
import logging

from utils.rate_limit import rate_limit
from utils.auth import login_required
from utils.favorites import get_favorites, is_favorited, add_favorite, remove_favorite
from utils.notification import get_notifications, get_unread_count, mark_as_read, mark_all_as_read, delete_notification, clear_all_notifications
from utils.writing_prompts import get_random_prompt, get_prompt_by_mood, get_all_categories, get_seasonal_prompt, get_time_based_prompt, get_prompts_by_category

logger = logging.getLogger(__name__)

api_bp = Blueprint('api', __name__)


@api_bp.route('/csrf-token')
@login_required
def get_csrf_token():
    """获取 CSRF 令牌"""
    from flask_wtf.csrf import generate_csrf
    return jsonify({
        'csrf_token': generate_csrf()
    })


# 收藏功能 API
@api_bp.route('/favorites')
@login_required
def get_favorites_api():
    """获取收藏列表"""
    user_id = session.get('user_id')
    favorites = get_favorites(user_id)
    return jsonify(favorites)


@api_bp.route('/favorites/<date_str>')
@login_required
def check_favorite_api(date_str):
    """检查是否已收藏"""
    user_id = session.get('user_id')
    return jsonify({'favorited': is_favorited(user_id, date_str)})


@api_bp.route('/favorites/<date_str>', methods=['POST'])
@login_required
@rate_limit(max_requests=100, window=60)
def add_favorite_api(date_str):
    """添加收藏"""
    user_id = session.get('user_id')
    title = request.json.get('title', '') if request.is_json else request.form.get('title', '')
    success = add_favorite(user_id, date_str, title)
    return jsonify({'success': success})


@api_bp.route('/favorites/<date_str>', methods=['DELETE'])
@login_required
@rate_limit(max_requests=100, window=60)
def remove_favorite_api(date_str):
    """移除收藏"""
    user_id = session.get('user_id')
    success = remove_favorite(user_id, date_str)
    return jsonify({'success': success})


# 通知功能 API
@api_bp.route('/notifications')
@login_required
def get_notifications_api():
    """获取通知列表"""
    limit = request.args.get('limit', type=int, default=20)
    notifications = get_notifications(limit=limit)
    unread_count = get_unread_count()
    return jsonify({
        'notifications': notifications,
        'unread_count': unread_count
    })


@api_bp.route('/notifications/mark-read/<notification_id>', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """标记单个通知为已读"""
    success = mark_as_read(notification_id)
    return jsonify({'success': success})


@api_bp.route('/notifications/mark-all-read', methods=['POST'])
@login_required
def mark_all_notifications_read():
    """标记所有通知为已读"""
    mark_all_as_read()
    return jsonify({'success': True})


@api_bp.route('/notifications/<notification_id>', methods=['DELETE'])
@login_required
def delete_notification_api(notification_id):
    """删除单个通知"""
    success = delete_notification(notification_id)
    return jsonify({'success': success})


@api_bp.route('/notifications/clear', methods=['POST'])
@login_required
def clear_notifications_api():
    """清空所有通知"""
    clear_all_notifications()
    return jsonify({'success': True})


# 写作提示 API
@api_bp.route('/prompts')
@login_required
def get_prompts_api():
    """获取写作提示"""
    mood_id = request.args.get('mood', type=int)
    category = request.args.get('category', '')
    seasonal = request.args.get('seasonal', 'false').lower() == 'true'
    time_based = request.args.get('time_based', 'false').lower() == 'true'
    
    if category:
        prompts = get_prompts_by_category(category)
    elif seasonal:
        prompts = [get_seasonal_prompt()]
    elif time_based:
        prompts = [get_time_based_prompt()]
    elif mood_id:
        prompts = [get_prompt_by_mood(mood_id)]
    else:
        prompts = [get_random_prompt()]
    
    categories = get_all_categories()
    
    return jsonify({
        'prompts': prompts,
        'categories': categories
    })


@api_bp.route('/prompts/random')
@login_required
def random_prompt_api():
    """获取随机写作提示"""
    prompt = get_random_prompt()
    return jsonify({'prompt': prompt})


@api_bp.route('/prompts/mood/<int:mood_id>')
@login_required
def mood_prompt_api(mood_id):
    """根据心情获取写作提示"""
    prompt = get_prompt_by_mood(mood_id)
    return jsonify({'prompt': prompt})
