import pytest
import os
import tempfile
from datetime import datetime

@pytest.fixture(scope='session')
def test_db():
    """创建测试数据库"""
    db_fd, db_path = tempfile.mkstemp()
    os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'
    os.environ['SECRET_KEY'] = 'test-secret-key'
    os.environ['ADMIN_PASSWORD'] = 'TestAdmin123!'
    
    yield db_path
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def app(test_db):
    """创建测试应用"""
    from app import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    
    yield flask_app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return app.test_client()


@pytest.fixture
def authenticated_client(client, app):
    """创建已认证的测试客户端"""
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['username'] = 'testuser'
        sess['role'] = 'user'
    return client
