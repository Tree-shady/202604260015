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
        original_env = os.environ.copy()
        
        os.environ['FLASK_ENV'] = 'testing'
        os.environ['DATABASE_URL'] = f'sqlite:///{temp_dir}/test.db'
        
        import importlib
        import sys
        if 'app' in sys.modules:
            del sys.modules['app']
        
        from app import app as flask_app
        flask_app.config['TESTING'] = True
        flask_app.config['WTF_CSRF_ENABLED'] = False
        
        with flask_app.app_context():
            from utils.models import init_db
            init_db(flask_app.config['SQLALCHEMY_DATABASE_URI'])
        
        yield flask_app
        
        for key, value in original_env.items():
            os.environ[key] = value
    
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
        """已认证的测试客户端 - 占位符"""
        return client
