from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from threading import local
from .config import DATE_FORMAT

Base = declarative_base()

_thread_local = local()

# 关联表
entry_tags = Table('entry_tags', Base.metadata,
    Column('entry_id', Integer, ForeignKey('entries.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user')
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Entry(Base):
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    date_str = Column(String(10), unique=True, nullable=False)  # YYYY-MM-DD
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # 关联
    tags = relationship('Tag', secondary=entry_tags, back_populates='entries')
    mood = relationship('Mood', back_populates='entry', uselist=False)
    images = relationship('Image', back_populates='entry', cascade='all, delete-orphan')

class Tag(Base):
    __tablename__ = 'tags'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    entries = relationship('Entry', secondary=entry_tags, back_populates='tags')

class Mood(Base):
    __tablename__ = 'moods'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey('entries.id'), unique=True, nullable=False)
    mood_type = Column(String(20), nullable=False, default='neutral')
    note = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # 关联
    entry = relationship('Entry', back_populates='mood')

class Image(Base):
    __tablename__ = 'images'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey('entries.id'), nullable=False)
    file_path = Column(String(255), nullable=False)
    filename = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # 关联
    entry = relationship('Entry', back_populates='images')

class Notification(Base):
    __tablename__ = 'notifications'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(20), nullable=False, default='info')  # info, warning, error, success
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

# 数据库引擎和会话
engine = None

def init_db(db_url):
    """初始化数据库"""
    global engine
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)

def get_session():
    """获取数据库会话（线程安全）"""
    if not hasattr(_thread_local, 'session'):
        if engine is None:
            raise RuntimeError("数据库未初始化，请先调用 init_db()")
        Session = sessionmaker(bind=engine)
        _thread_local.session = Session()
    return _thread_local.session

def close_db():
    """关闭当前线程的数据库连接"""
    if hasattr(_thread_local, 'session'):
        _thread_local.session.close()
        del _thread_local.session
