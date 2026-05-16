import pytest
from utils.validation import validate_date_str, validate_tag, sanitize_tag, sanitize_tags


def test_validate_date_str():
    """测试日期字符串验证"""
    assert validate_date_str("2024-01-01") is True
    assert validate_date_str("2024-12-31") is True
    assert validate_date_str("2024-02-29") is True
    assert validate_date_str("2024-13-01") is False
    assert validate_date_str("2024-01-32") is False
    assert validate_date_str("2024-1-1") is False
    assert validate_date_str("2024/01/01") is False
    assert validate_date_str("") is False


def test_validate_tag():
    """测试标签验证"""
    assert validate_tag("工作") is True
    assert validate_tag("生活") is True
    assert validate_tag("work") is True
    assert validate_tag("test123") is True
    assert validate_tag("") is False
    assert validate_tag("a" * 31) is False
    assert validate_tag("tag with space") is False
    assert validate_tag("tag,special") is False


def test_sanitize_tag():
    """测试标签转义"""
    assert sanitize_tag("  工作  ") == "工作"
    assert sanitize_tag("<script>") == "&lt;script&gt;"
    assert sanitize_tag("' OR '1'='1") == "&#39; OR &#39;1&#39;&#61;&#39;1"


def test_sanitize_tags():
    """测试多标签转义"""
    tags = sanitize_tags("工作,生活,<script>")
    assert "工作" in tags
    assert "生活" in tags
    assert "&lt;script&gt;" in tags
    
    assert sanitize_tags("") == []
    assert sanitize_tags("  ") == []
