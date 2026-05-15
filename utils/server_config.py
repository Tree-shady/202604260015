"""
服务器配置模块

包含开发和生产服务器的配置和启动逻辑
"""
import os
import logging
from typing import Optional
from flask import Flask


logger = logging.getLogger(__name__)


def get_server_config() -> dict:
    """
    获取服务器配置
    
    Returns:
        包含服务器配置的字典
    """
    return {
        'host': os.environ.get('FLASK_HOST', '0.0.0.0'),
        'port': int(os.environ.get('FLASK_PORT', 5000)),
        'debug': os.environ.get('FLASK_ENV', 'development') != 'production',
        'bind_address': os.environ.get('BIND_ADDRESS', '0.0.0.0:5000'),
        'gunicorn_workers': int(os.environ.get('GUNICORN_WORKERS', 4))
    }


def print_server_info(host: str, port: int) -> None:
    """
    打印服务器启动信息
    
    Args:
        host: 主机地址
        port: 端口号
    """
    print(f"\n{'=' * 60}")
    print(f"  日记本 Web 服务器")
    print(f"{'=' * 60}")
    print(f"  本地访问:  http://127.0.0.1:{port}")
    print(f"  远程访问:  http://<服务器IP>:{port}")
    print(f"  生产模式:  请设置 FLASK_ENV=production")
    print(f"{'=' * 60}")
    print(f"  提示: 确保防火墙允许 {port} 端口入站")
    print(f"{'=' * 60}\n")


def run_development_server(app: Flask) -> None:
    """
    运行开发服务器
    
    Args:
        app: Flask应用实例
    """
    config = get_server_config()
    host = config['host']
    port = config['port']

    logger.info(f"启动开发服务器 - 地址: http://{host}:{port}")
    print_server_info(host, port)

    app.run(host=host, port=port, debug=True)


def run_production_server(app: Flask) -> None:
    """
    运行生产服务器
    
    Args:
        app: Flask应用实例
    """
    if not os.environ.get('SECRET_KEY'):
        logger.warning("生产环境未设置 SECRET_KEY 环境变量，使用默认值")

    try:
        from gunicorn.app.wsgiapp import WSGIApplication
    except ImportError:
        logger.warning("Gunicorn 未安装，将使用 Flask 内置服务器")
        run_development_server(app)
        return

    config = get_server_config()
    bind = config['bind_address']
    workers = config['gunicorn_workers']

    logger.info(f"启动生产服务器 - 绑定地址: {bind}, 工作进程数: {workers}")

    # 使用 Gunicorn 运行
    app_for_gunicorn = WSGIApplication()
    app_for_gunicorn.load_wsgiapp()
    app_for_gunicorn.cfg.set({
        'bind': bind,
        'workers': workers,
        'worker_class': 'sync',
        'timeout': 120,
        'keepalive': 5,
        'accesslog': '-',
        'errorlog': '-',
        'loglevel': 'info'
    })
    app_for_gunicorn.run()
