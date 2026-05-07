#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日记收藏管理模块
"""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
FAVORITES_FILE = Path("data") / "favorites.json"

def _ensure_file():
    """确保收藏文件存在"""
    FAVORITES_FILE.parent.mkdir(exist_ok=True)
    if not FAVORITES_FILE.exists():
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

def get_favorites(user_id: int) -> List[Dict]:
    """获取用户的收藏列表"""
    _ensure_file()
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            all_favorites = json.load(f)
        return all_favorites.get(str(user_id), [])
    except Exception as e:
        logger.error(f"获取收藏失败: {e}")
        return []

def is_favorited(user_id: int, date_str: str) -> bool:
    """检查日记是否已收藏"""
    favorites = get_favorites(user_id)
    return any(f['date'] == date_str for f in favorites)

def add_favorite(user_id: int, date_str: str, title: str = "") -> bool:
    """添加收藏"""
    _ensure_file()
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            all_favorites = json.load(f)
        
        if str(user_id) not in all_favorites:
            all_favorites[str(user_id)] = []
        
        # 检查是否已存在
        if is_favorited(user_id, date_str):
            return False
        
        favorite = {
            'date': date_str,
            'title': title,
            'created_at': datetime.now().isoformat()
        }
        all_favorites[str(user_id)].insert(0, favorite)
        
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_favorites, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"添加收藏失败: {e}")
        return False

def remove_favorite(user_id: int, date_str: str) -> bool:
    """移除收藏"""
    _ensure_file()
    try:
        with open(FAVORITES_FILE, 'r', encoding='utf-8') as f:
            all_favorites = json.load(f)
        
        if str(user_id) in all_favorites:
            all_favorites[str(user_id)] = [
                f for f in all_favorites[str(user_id)]
                if f['date'] != date_str
            ]
        
        with open(FAVORITES_FILE, 'w', encoding='utf-8') as f:
            json.dump(all_favorites, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"移除收藏失败: {e}")
        return False

def get_favorite_count(user_id: int) -> int:
    """获取收藏数量"""
    return len(get_favorites(user_id))
