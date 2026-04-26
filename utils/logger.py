import logging
import sys
from pathlib import Path
from datetime import datetime

LOG_DIR = Path("logs")
LOG_FILE = LOG_DIR / "diary.log"

def setup_logger(name="diary", level=logging.INFO):
    """设置日志记录器"""
    LOG_DIR.mkdir(exist_ok=True)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 文件处理器
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.WARNING)
    
    # 格式化
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

def log_action(action, details=""):
    """记录用户操作"""
    logger = setup_logger()
    if details:
        logger.info(f"{action}: {details}")
    else:
        logger.info(action)

def log_error(error, details=""):
    """记录错误"""
    logger = setup_logger()
    if details:
        logger.error(f"{error}: {details}")
    else:
        logger.error(error)

def log_warning(warning, details=""):
    """记录警告"""
    logger = setup_logger()
    if details:
        logger.warning(f"{warning}: {details}")
    else:
        logger.warning(warning)
