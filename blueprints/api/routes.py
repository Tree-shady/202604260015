from flask import render_template, request, redirect, url_for, flash, session, jsonify
from utils.auth import login_required, admin_required
from utils.notification import (
    get_notifications,
    get_unread_count,
    mark_as_read,
    mark_all_as_read,
    delete_notification,
    clear_all_notifications
)
from utils.favorites import get_favorites, is_favorited, add_favorite, remove_favorite, get_favorite_count
from utils.writing_prompts import (
    get_random_prompt,
    get_prompt_by_mood,
    get_all_categories,
    get_seasonal_prompt,
    get_time_based_prompt,
    get_prompts_by_category
)
from utils.rate_limit import rate_limit
from utils.db_manager import db_manager
from utils.config import get_config, save_config
from . import api_bp
from flask_wtf.csrf import validate_csrf, CSRFError
import logging

logger = logging.getLogger(__name__)


@api_bp.route('/notifications')
@rate_limit(max_requests=30, window=60)
def get_notifications_api():
    """获取通知列表API"""
    limit = request.args.get('limit', 50, type=int)
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'

    notifications = get_notifications(limit=limit, unread_only=unread_only)
    unread_count = get_unread_count()

    return jsonify({
        'notifications': notifications,
        'unread_count': unread_count
    })


@api_bp.route('/notifications/mark-read/<notification_id>', methods=['POST'])
def mark_notification_read(notification_id):
    """标记单个通知为已读"""
    success = mark_as_read(notification_id)
    return jsonify({'success': success})


@api_bp.route('/notifications/mark-all-read', methods=['POST'])
def mark_all_notifications_read():
    """标记所有通知为已读"""
    mark_all_as_read()
    return jsonify({'success': True})


@api_bp.route('/notifications/<notification_id>', methods=['DELETE'])
def delete_notification_api(notification_id):
    """删除单个通知"""
    success = delete_notification(notification_id)
    return jsonify({'success': success})


@api_bp.route('/notifications/clear', methods=['POST'])
def clear_notifications_api():
    """清空所有通知"""
    clear_all_notifications()
    return jsonify({'success': True})


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
@rate_limit(max_requests=20, window=60)
def add_favorite_api(date_str):
    """添加收藏"""
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


@api_bp.route('/favorites/<date_str>', methods=['DELETE'])
@login_required
@rate_limit(max_requests=20, window=60)
def remove_favorite_api(date_str):
    """移除收藏"""
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


@api_bp.route('/prompts')
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


@api_bp.route('/prompts/categories')
@login_required
def get_prompt_categories_api():
    """获取所有提示分类"""
    return jsonify(get_all_categories())


@api_bp.route('/prompts/batch')
@login_required
def get_batch_prompts_api():
    """批量获取提示"""
    category = request.args.get('category', 'daily')
    count = int(request.args.get('count', 3))
    prompts = get_prompts_by_category(category, count)
    return jsonify(prompts)


@api_bp.route('/test-database', methods=['POST'])
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
