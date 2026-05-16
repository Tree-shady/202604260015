import pytest
from utils.models import User, Entry, Tag, Mood


def test_user_model_to_dict():
    """测试用户模型转字典"""
    user = User(
        username='testuser',
        password_hash='hash123',
        role='user',
        active=True
    )
    
    user_dict = user.to_dict()
    
    assert user_dict['username'] == 'testuser'
    assert user_dict['role'] == 'user'
    assert user_dict['is_active'] is True
    assert 'password_hash' not in user_dict


def test_user_model_to_dict_with_password():
    """测试用户模型转字典（包含密码）"""
    user = User(
        username='testuser',
        password_hash='hash123',
        role='user'
    )
    
    user_dict = user.to_dict(include_password=True)
    
    assert 'password_hash' in user_dict
    assert user_dict['password_hash'] == 'hash123'


def test_entry_model():
    """测试日记模型"""
    entry = Entry(
        user_id=1,
        date_str='2024-01-01',
        content='测试内容'
    )
    
    assert entry.user_id == 1
    assert entry.date_str == '2024-01-01'
    assert entry.content == '测试内容'


def test_tag_model():
    """测试标签模型"""
    tag = Tag(name='测试标签')
    
    assert tag.name == '测试标签'


def test_mood_model():
    """测试心情模型"""
    mood = Mood(
        mood_type='happy',
        note='今天很开心'
    )
    
    assert mood.mood_type == 'happy'
    assert mood.note == '今天很开心'
