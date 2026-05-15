"""
安全头管理模块
"""
from flask import Response


def add_security_headers(response: Response) -> Response:
    """
    为响应添加安全头
    
    Args:
        response: Flask响应对象
        
    Returns:
        添加了安全头的响应对象
    """
    # 防止 MIME 类型嗅探
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # 防止点击劫持
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    # XSS 保护
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # 内容安全策略 - 虽然保留了 unsafe-inline/unsafe-eval 以保证兼容性，但添加了更多限制
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "font-src 'self' https://cdn.jsdelivr.net; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "  # 禁止 Flash 等不安全插件
        "base-uri 'self'; "    # 限制 base 标签
        "form-action 'self'; " # 限制表单提交
        "frame-ancestors 'self';"  # 防止点击劫持（替代 X-Frame-Options）
    )
    # 引用策略
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # 权限策略
    response.headers['Permissions-Policy'] = (
        'geolocation=(), microphone=(), camera=(), payment=(), usb=(), bluetooth=()'
    )
    return response
