import json
from pathlib import Path

CONFIG_FILE = Path("config.json")
ENTRIES_DIR = Path("entries")
TAGS_FILE = Path("tags.json")
IMAGES_DIR = Path("images")
DATE_FORMAT = "%Y-%m-%d"

# 配置缓存
_config_cache = None

# 默认配置
DEFAULT_CONFIG = {
    "theme": "light",  # light, dark
    "date_format": "%Y-%m-%d",
    "backup_enabled": True,
    "backup_interval": 7,  # 天
    "auto_save": True,
    "auto_save_interval": 30,  # 自动保存间隔（秒）
    "editor_font_size": 12,
    "terminal_colors": {
        "primary": "GREEN",
        "secondary": "CYAN",
        "accent": "YELLOW",
        "text": "WHITE",
        "muted": "LIGHTBLACK_EX",
        "error": "RED",
        "success": "GREEN",
        "info": "BLUE"
    },
    "notifications": {
        "enabled": True,
        "level": "info"  # info, warning, error
    }
}

def load_config():
    """加载配置文件"""
    global _config_cache
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 合并默认配置
            for key, value in DEFAULT_CONFIG.items():
                if key not in config:
                    config[key] = value
            _config_cache = config  # 更新缓存
            return config
        except json.JSONDecodeError:
            _config_cache = DEFAULT_CONFIG  # 更新缓存
            return DEFAULT_CONFIG
    _config_cache = DEFAULT_CONFIG  # 更新缓存
    return DEFAULT_CONFIG

def save_config(config):
    """保存配置文件"""
    global _config_cache
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    _config_cache = config  # 更新缓存

def get_config():
    """获取配置（带缓存）"""
    global _config_cache
    if _config_cache is None:
        return load_config()
    return _config_cache

def update_config(key, value):
    """更新配置"""
    config = get_config()
    config[key] = value
    save_config(config)

def reset_config():
    """重置配置到默认值"""
    global _config_cache
    save_config(DEFAULT_CONFIG)
    _config_cache = DEFAULT_CONFIG  # 更新缓存
    return DEFAULT_CONFIG
