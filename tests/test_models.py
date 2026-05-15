import pytest
from datetime import datetime, timedelta


class TestModels:
    """数据模型测试"""
    
    def test_entry_creation(self, app):
        """测试日记创建"""
        from utils.models import Entry, init_db, get_session
        
        with app.app_context():
            session = get_session()
            entry = Entry(
                date_str='2024-01-15',
                title='Test Entry',
                content='This is a test entry.'
            )
            session.add(entry)
            session.commit()
            
            saved_entry = session.query(Entry).filter_by(title='Test Entry').first()
            assert saved_entry is not None
            assert saved_entry.content == 'This is a test entry.'
    
    def test_tag_creation(self, app):
        """测试标签创建"""
        from utils.models import Tag, Entry, get_session
        
        with app.app_context():
            session = get_session()
            tag = Tag(name='test-tag')
            session.add(tag)
            session.commit()
            
            saved_tag = session.query(Tag).filter_by(name='test-tag').first()
            assert saved_tag is not None
    
    def test_mood_creation(self, app):
        """测试心情创建"""
        from utils.models import Mood, get_session
        
        with app.app_context():
            session = get_session()
            mood = Mood(
                date_str='2024-01-15',
                score=4,
                note='Feeling good'
            )
            session.add(mood)
            session.commit()
            
            saved_mood = session.query(Mood).filter_by(date_str='2024-01-15').first()
            assert saved_mood is not None
            assert saved_mood.score == 4


class TestDatabaseOperations:
    """数据库操作测试"""
    
    def test_database_initialization(self, app):
        """测试数据库初始化"""
        from utils.models import init_db
        
        with app.app_context():
            session = get_session()
            assert session is not None
    
    def test_entry_with_tags(self, app):
        """测试带标签的日记"""
        from utils.models import Entry, Tag, get_session
        
        with app.app_context():
            session = get_session()
            entry = Entry(date_str='2024-01-15', title='Tagged Entry')
            tag = Tag(name='important')
            entry.tags.append(tag)
            session.add(entry)
            session.commit()
            
            saved_entry = session.query(Entry).filter_by(title='Tagged Entry').first()
            assert len(saved_entry.tags) == 1
            assert saved_entry.tags[0].name == 'important'
