import pytest
from datetime import datetime


class TestDateValidation:
    """日期验证测试"""
    
    def test_valid_date_format(self):
        """测试有效日期格式"""
        from utils.validation import validate_date_str
        assert validate_date_str('2024-01-15') == True
        assert validate_date_str('2024-12-31') == True
    
    def test_invalid_date_format(self):
        """测试无效日期格式"""
        from utils.validation import validate_date_str
        assert validate_date_str('01-15-2024') == False
        assert validate_date_str('2024/01/15') == False
        assert validate_date_str('invalid') == False
    
    def test_invalid_dates(self):
        """测试无效日期"""
        from utils.validation import validate_date_str
        assert validate_date_str('2024-13-01') == False
        assert validate_date_str('2024-02-30') == False


class TestTagValidation:
    """标签验证测试"""
    
    def test_valid_tag(self):
        """测试有效标签"""
        from utils.validation import validate_tag
        assert validate_tag('python') == True
        assert validate_tag('work') == True
    
    def test_invalid_tag_empty(self):
        """测试空标签"""
        from utils.validation import validate_tag
        assert validate_tag('') == False
        assert validate_tag('   ') == False
    
    def test_sanitize_tags(self):
        """测试标签清理"""
        from utils.validation import sanitize_tags
        tags = ['  python  ', 'work', 'life']
        result = sanitize_tags(tags)
        assert 'python' in result
        assert 'work' in result


class TestSecurityUtils:
    """安全工具测试"""
    
    def test_password_hashing(self):
        """测试密码哈希"""
        from utils.auth import hash_password, verify_password
        
        password = 'test_password_123'
        hashed = hash_password(password)
        
        assert hashed != password
        assert verify_password(password, hashed) == True
        assert verify_password('wrong_password', hashed) == False
    
    def test_session_token_generation(self):
        """测试会话令牌生成"""
        from utils.auth import generate_session_token
        
        token1 = generate_session_token()
        token2 = generate_session_token()
        
        assert token1 != token2
        assert len(token1) > 20
