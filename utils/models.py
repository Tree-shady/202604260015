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

entry_tags = Table('entry_tags', Base.metadata,
    Column('entry_id', Integer, ForeignKey('entries.id'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id'), primary_key=True)
)

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default='user', index=True)
    active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    password_set_at = Column(DateTime, default=datetime.utcnow)
    password_expires_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_temporary = Column(Boolean, default=False)
    settings = Column(Text, default='{}')
    
    # 连续打卡相关
    current_streak = Column(Integer, default=0)  # 当前连续打卡天数
    longest_streak = Column(Integer, default=0)  # 最长连续打卡天数
    last_entry_date = Column(String(10), nullable=True, index=True)  # 最后写日记的日期
    total_entries = Column(Integer, default=0)  # 总日记数

    entries = relationship('Entry', back_populates='user', cascade='all, delete-orphan')
    
    def to_dict(self, include_password=False):
        """转换为字典格式"""
        # 检查并更新过期状态
        now = datetime.utcnow()
        if self.expires_at and self.expires_at < now and self.active:
            self.active = False
        
        # 检查密码是否过期
        password_expired = False
        if self.password_expires_at and self.password_expires_at < now:
            password_expired = True
        
        result = {
            'id': self.id,
            'username': self.username,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.active,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_temporary': self.is_temporary,
            'password_expired': password_expired,
            'password_expires_at': self.password_expires_at.isoformat() if self.password_expires_at else None
        }
        
        if include_password:
            result['password_hash'] = self.password_hash
        
        return result

class Entry(Base):
    __tablename__ = 'entries'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    date_str = Column(String(10), nullable=False, index=True)
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship('User', back_populates='entries')
    tags = relationship('Tag', secondary=entry_tags, back_populates='entries', lazy='selectin')
    mood = relationship('Mood', back_populates='entry', uselist=False, cascade='all, delete-orphan', lazy='selectin')
    images = relationship('Image', back_populates='entry', cascade='all, delete-orphan', lazy='selectin')

class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    entries = relationship('Entry', secondary=entry_tags, back_populates='tags')

class Mood(Base):
    __tablename__ = 'moods'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey('entries.id'), unique=True, nullable=False)
    mood_type = Column(String(20), nullable=False, default='neutral')
    note = Column(String(200))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    entry = relationship('Entry', back_populates='mood')

class Image(Base):
    __tablename__ = 'images'

    id = Column(Integer, primary_key=True, autoincrement=True)
    entry_id = Column(Integer, ForeignKey('entries.id'), nullable=False)
    file_path = Column(String(255), nullable=False)
    filename = Column(String(100), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    entry = relationship('Entry', back_populates='images')

class Notification(Base):
    __tablename__ = 'notifications'

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String(20), nullable=False, default='info')
    read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class LoginAttempt(Base):
    __tablename__ = 'login_attempts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45), nullable=True)
    attempt_time = Column(DateTime, default=datetime.utcnow, index=True)
    success = Column(Boolean, default=False)

engine = None
_session_factory = None

def init_db(db_url):
    global engine, _session_factory
    # 添加连接池配置，提高性能
    engine = create_engine(
        db_url,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_recycle=3600,
        echo=False
    )
    Base.metadata.create_all(engine)
    _session_factory = sessionmaker(bind=engine)

def get_session():
    if not hasattr(_thread_local, 'session'):
        if _session_factory is None:
            raise RuntimeError("数据库未初始化，请先调用 init_db()")
        _thread_local.session = _session_factory()
    return _thread_local.session

def close_db():
    if hasattr(_thread_local, 'session'):
        _thread_local.session.close()
        del _thread_local.session


from contextlib import contextmanager


@contextmanager
def db_transaction():
    """数据库事务上下文管理器
    
    使用示例:
        with db_transaction() as db:
            user = db.query(User).get(1)
            # 操作...
    
    自动处理提交/回滚和关闭
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        close_db()
