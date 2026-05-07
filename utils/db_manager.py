#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接管理模块 - 支持本地和远程数据库
"""

import os
import json
from pathlib import Path
from urllib.parse import quote_plus
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from threading import local

_thread_local = local()

# 数据库连接配置
DATA_DIR = Path("data")
DATA_DIR.mkdir(exist_ok=True)
DATABASE_CONFIG_FILE = DATA_DIR / 'database_config.json'

class DatabaseManager:
    def __init__(self):
        self.engines = {}
        self.current_db_type = 'local'

    def load_config(self):
        """加载数据库配置"""
        if DATABASE_CONFIG_FILE.exists():
            try:
                with open(DATABASE_CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {}

    def save_config(self, config):
        """保存数据库配置"""
        with open(DATABASE_CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)

    def get_database_url(self, db_type='local'):
        """获取数据库连接URL"""
        config = self.load_config()
        
        if db_type == 'remote':
            remote_config = config.get('remote', {})
            db_type = os.environ.get('DB_TYPE', remote_config.get('type', 'postgresql'))
            host = os.environ.get('DB_HOST', remote_config.get('host', 'localhost'))
            port = int(os.environ.get('DB_PORT', remote_config.get('port', 5432)))
            database = os.environ.get('DB_NAME', remote_config.get('database', 'diary'))
            username = os.environ.get('DB_USERNAME', remote_config.get('username', 'user'))
            password = os.environ.get('DB_PASSWORD', remote_config.get('password', ''))
            
            if password:
                encoded_password = quote_plus(password)
                return f"{db_type}://{username}:{encoded_password}@{host}:{port}/{database}"
            else:
                return f"{db_type}://{username}@{host}:{port}/{database}"
        else:
            return os.environ.get('DATABASE_URL', 'sqlite:///diary.db')

    def init_database(self, db_type='local'):
        """初始化数据库连接"""
        global engine
        
        db_url = self.get_database_url(db_type)
        engine = create_engine(db_url)
        
        from utils.models import Base
        Base.metadata.create_all(engine)
        
        self.current_db_type = db_type
        
        config = self.load_config()
        config['current_db'] = db_type
        self.save_config(config)
        
        return engine

    def switch_database(self, db_type):
        """切换数据库类型"""
        if db_type not in ['local', 'remote']:
            raise ValueError("数据库类型必须是 'local' 或 'remote'")
        
        # 关闭当前会话
        close_db()
        
        # 初始化新数据库
        self.init_database(db_type)

    def set_remote_config(self, host, port, database, username, password, db_type='postgresql'):
        """设置远程数据库配置"""
        config = self.load_config()
        config['remote'] = {
            'type': db_type,
            'host': host,
            'port': port,
            'database': database,
            'username': username,
            'password': password
        }
        self.save_config(config)

    def get_current_db_type(self):
        """获取当前数据库类型"""
        return self.current_db_type

    def is_remote_configured(self):
        """检查远程数据库是否已配置"""
        config = self.load_config()
        remote = config.get('remote', {})
        return all([remote.get('host'), remote.get('database'), remote.get('username')])


# 全局数据库连接
engine = None

def get_session():
    """获取数据库会话"""
    if not hasattr(_thread_local, 'session'):
        if engine is None:
            raise RuntimeError("数据库未初始化，请先调用 init_db()")
        Session = sessionmaker(bind=engine)
        _thread_local.session = Session()
    return _thread_local.session

def close_db():
    """关闭数据库会话"""
    if hasattr(_thread_local, 'session'):
        _thread_local.session.close()
        del _thread_local.session

# 创建全局数据库管理器实例
db_manager = DatabaseManager()

def init_db(db_url=None):
    """初始化数据库（兼容旧接口）"""
    global engine
    
    if db_url:
        engine = create_engine(db_url)
    else:
        db_type = db_manager.get_current_db_type()
        engine = db_manager.init_database(db_type)
    
    from utils.models import Base, init_db as models_init_db
    Base.metadata.create_all(engine)
    models_init_db('sqlite:///diary.db')