#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文件系统到数据库的数据迁移脚本
"""

import os
import json
from pathlib import Path
from datetime import datetime

from utils.models import init_db, get_session
from utils.storage import ENTRIES_DIR
from utils.logger import setup_logger
from utils.auth import create_user

logger = setup_logger()


def parse_entry_content(content):
    """解析日记文件内容"""
    lines = content.split('\n')
    timestamp = None
    tags = []
    content_lines = []

    for i, line in enumerate(lines):
        if line.startswith('[') and ']' in line:
            try:
                timestamp_str = line[1:-1]
                if ' ' in timestamp_str:
                    timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                pass
        elif line.startswith('Tags: '):
            tag_str = line[6:].strip()
            if tag_str:
                tags = [t.strip() for t in tag_str.split(',') if t.strip()]
        else:
            content_lines.append(line)

    return timestamp, tags, '\n'.join(content_lines)


def migrate_entries_to_db(user_id=1):
    """迁移日记条目到数据库"""
    session = get_session()

    entries_dir = ENTRIES_DIR
    if not entries_dir.exists():
        logger.info(f"日记目录不存在: {entries_dir}")
        return

    count = 0
    entries_files = list(entries_dir.glob('*.txt'))

    logger.info(f"开始迁移日记文件，共 {len(entries_files)} 个")

    for entry_file in entries_files:
        date_str = entry_file.stem

        try:
            with open(entry_file, 'r', encoding='utf-8') as f:
                content = f.read()

            timestamp, tags, body = parse_entry_content(content)
            if not timestamp:
                timestamp = datetime.now()

            from utils.models import Entry, Tag
            existing_entry = session.query(Entry).filter_by(date_str=date_str, user_id=user_id).first()
            if existing_entry:
                logger.info(f"日记已存在，跳过: {date_str}")
                continue

            entry = Entry(user_id=user_id, date_str=date_str, content=body, timestamp=timestamp)
            session.add(entry)
            session.flush()

            for tag_name in tags:
                tag = session.query(Tag).filter_by(name=tag_name).first()
                if not tag:
                    tag = Tag(name=tag_name)
                    session.add(tag)
                entry.tags.append(tag)

            session.commit()
            count += 1
            logger.info(f"成功迁移: {date_str}")
        except Exception as e:
            logger.error(f"迁移失败 {date_str}: {e}")
            session.rollback()

    logger.info(f"迁移完成，成功迁移 {count} 个日记")


def migrate_tags_index(user_id=1):
    """迁移标签索引"""
    from utils.storage import TAGS_FILE

    if not TAGS_FILE.exists():
        logger.info("标签索引文件不存在")
        return

    try:
        with open(TAGS_FILE, 'r', encoding='utf-8') as f:
            tag_data = json.load(f)

        logger.info(f"加载标签数据成功，共 {len(tag_data)} 个标签")
        # 实际标签迁移已经在上面的日记迁移过程中处理了
    except Exception as e:
        logger.error(f"迁移标签索引失败: {e}")


def migrate_moods(user_id=1):
    """迁移心情记录"""
    from utils.mood import MOOD_FILE
    if not MOOD_FILE.exists():
        logger.info("心情记录文件不存在")
        return

    try:
        with open(MOOD_FILE, 'r', encoding='utf-8') as f:
            mood_data = json.load(f)

        session = get_session()
        count = 0

        for date_str, record in mood_data.items():
            from utils.models import Mood
            existing = session.query(Mood).filter_by(date_str=date_str, user_id=user_id).first()
            if existing:
                continue

            mood = Mood(
                user_id=user_id,
                date_str=date_str,
                mood_type=record.get('mood', 'neutral'),
                note=record.get('note', '')
            )
            session.add(mood)
            count += 1

        session.commit()
        logger.info(f"成功迁移 {count} 条心情记录")
    except Exception as e:
        logger.error(f"迁移心情记录失败: {e}")


def initialize_default_users():
    """初始化默认用户"""
    logger.info("初始化默认用户...")

    try:
        create_user('admin', 'admin123', role='admin')
        logger.info("创建管理员用户: admin")
    except Exception as e:
        logger.info(f"管理员用户可能已存在: {e}")

    try:
        create_user('superadmin', 'admin123', role='superadmin')
        logger.info("创建超级管理员用户: superadmin")
    except Exception as e:
        logger.info(f"超级管理员用户可能已存在: {e}")


def main():
    """主迁移函数"""
    print("=" * 50)
    print("文件系统到数据库的迁移工具")
    print("=" * 50)

    print("\n[1] 初始化数据库...")
    init_db('sqlite:///diary.db')
    print("✓ 数据库初始化完成")

    print("\n[2] 初始化默认用户...")
    initialize_default_users()
    print("✓ 默认用户初始化完成")

    print("\n[3] 迁移日记条目...")
    migrate_entries_to_db()
    print("✓ 日记条目迁移完成")

    print("\n[4] 迁移标签索引...")
    migrate_tags_index()
    print("✓ 标签索引迁移完成")

    print("\n[5] 迁移心情记录...")
    migrate_moods()
    print("✓ 心情记录迁移完成")

    print("\n" + "=" * 50)
    print("迁移完成！")
    print("=" * 50)
    print("\n默认登录账号：")
    print("  管理员: admin / admin123")
    print("  超级管理员: superadmin / admin123")


if __name__ == "__main__":
    main()

