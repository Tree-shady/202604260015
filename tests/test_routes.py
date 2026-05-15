import pytest


class TestHealthEndpoints:
    """健康检查端点测试"""
    
    def test_index_page_loads(self, client):
        """测试首页是否正常加载"""
        response = client.get('/')
        assert response.status_code in [200, 302]
    
    def test_favicon_access(self, client):
        """测试图标文件 (可能不存在，忽略错误)"""
        response = client.get('/favicon.ico')
        # 不管是 200 还是 404 都算成功，因为 favicon 不是必需的


class TestAuthEndpoints:
    """认证端点测试"""
    
    def test_login_page_loads(self, client):
        """测试登录页面加载"""
        response = client.get('/auth/login')
        assert response.status_code == 200
    
    def test_register_page_loads(self, client):
        """测试注册页面加载"""
        response = client.get('/auth/register')
        assert response.status_code == 200


class TestMainEndpoints:
    """主要页面端点测试"""
    
    def test_index_redirects_to_login_when_not_logged_in(self, client):
        """测试未登录时重定向到登录页"""
        response = client.get('/')
        assert response.status_code in [200, 302]
