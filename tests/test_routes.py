import pytest


class TestHealthEndpoints:
    """健康检查端点测试"""
    
    def test_index_page_loads(self, client):
        """测试首页是否正常加载"""
        response = client.get('/')
        assert response.status_code in [200, 302]
    
    def test_static_files_accessible(self, client):
        """测试静态文件是否可访问"""
        response = client.get('/favicon.ico')
        assert response.status_code in [200, 404]


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
    
    def test_login_with_invalid_data(self, client):
        """测试无效登录数据"""
        response = client.post('/auth/login', data={})
        assert response.status_code == 200
    
    def test_logout_requires_login(self, client):
        """测试登出需要登录"""
        response = client.get('/auth/logout', follow_redirects=True)
        assert response.status_code == 200


class TestMainEndpoints:
    """主要页面端点测试"""
    
    def test_entries_list_loads(self, authenticated_client):
        """测试日记列表页面"""
        response = authenticated_client.get('/entries')
        assert response.status_code == 200
    
    def test_new_entry_page_loads(self, authenticated_client):
        """测试新建日记页面"""
        response = authenticated_client.get('/new')
        assert response.status_code == 200
    
    def test_stats_page_loads(self, authenticated_client):
        """测试统计页面"""
        response = authenticated_client.get('/stats')
        assert response.status_code == 200
    
    def test_search_page_loads(self, authenticated_client):
        """测试搜索页面"""
        response = authenticated_client.get('/search')
        assert response.status_code == 200


class TestAPIEndpoints:
    """API 端点测试"""
    
    def test_api_health_check(self, client):
        """测试 API 健康检查"""
        response = client.get('/api/health')
        assert response.status_code in [200, 404]
    
    def test_api_entries_requires_auth(self, client):
        """测试 API 需要认证"""
        response = client.get('/api/entries')
        assert response.status_code == 401
