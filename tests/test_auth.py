import pytest
from utils.auth import hash_password, verify_password, get_users, create_user, delete_user
from utils.models import init_db, User, get_session
import os


def test_password_hashing():
    """测试密码哈希"""
    password = "TestPassword123!"
    hashed = hash_password(password)
    
    assert hashed != password
    assert '$' in hashed
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)


def test_password_hashing_with_salt():
    """测试带盐值的密码哈希"""
    password = "TestPassword123!"
    salt = "custom-salt-value"
    hashed = hash_password(password, salt)
    
    assert hashed.startswith(salt)
    assert verify_password(password, hashed)


def test_user_creation():
    """测试用户创建"""
    init_db(os.environ.get('DATABASE_URL', 'sqlite:///test.db'))
    
    username = f"testuser_{datetime.now().timestamp()}"
    password = "TestPass123!"
    
    success, message = create_user(username, password)
    
    assert success is True
    assert "成功" in message


def test_duplicate_user_creation():
    """测试重复用户创建"""
    init_db(os.environ.get('DATABASE_URL', 'sqlite:///test.db'))
    
    username = f"testuser_{datetime.now().timestamp()}"
    password = "TestPass123!"
    
    create_user(username, password)
    success, message = create_user(username, password)
    
    assert success is False
    assert "已存在" in message


def test_get_users():
    """测试获取用户列表"""
    init_db(os.environ.get('DATABASE_URL', 'sqlite:///test.db'))
    
    users = get_users()
    
    assert isinstance(users, list)
