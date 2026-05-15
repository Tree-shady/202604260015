import pytest
import os
import tempfile
from pathlib import Path


class TestConfig:
    """测试配置"""
    
    @pytest.fixture
    def temp_dir(self):
        """创建临时目录用于测试"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.fixture
    def app(self, temp_dir):
        """创建测试用 Flask 应用"""
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['DATABASE_URL'] = f'sqlite:///{temp_dir}/test.db'
        
        from app import create_app
        app = create_app()
        app.config['TESTING'] = True
        yield app
    
    @pytest.fixture
    def client(self, app):
        """测试客户端"""
        return app.test_client()
    
    @pytest.fixture
    def runner(self, app):
        """CLI 测试运行器"""
        return app.test_cli_runner()
    
    @pytest.fixture
    def authenticated_client(self, client):
        """已认证的测试客户端"""
        client.post('/auth/login', data={
            'username': 'testuser',
            'password': 'testpassword'
        })
        return client
