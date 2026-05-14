import json
from pathlib import Path
from typing import Dict, Any, Optional

CONFIG_FILE = Path("config.json")
ENTRIES_DIR = Path("entries")
TAGS_FILE = Path("tags.json")
MOODS_FILE = Path("moods.json")
IMAGES_DIR = Path("images")
DATE_FORMAT = "%Y-%m-%d"

# 配置缓存
_config_cache: Optional[Dict[str, Any]] = None

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
    },
    "greetings": {
        "enabled": True,
        "source": "local",  # local, api
        "show_on_startup": True
    }
}

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """验证并修复配置
    
    Args:
        config: 待验证的配置
        
    Returns:
        验证并修复后的配置
    """
    validated = DEFAULT_CONFIG.copy()
    
    # 合并用户配置
    for key, value in config.items():
        if key in validated:
            # 验证主题
            if key == "theme":
                if value not in ["light", "dark"]:
                    value = "light"
            # 验证数字类型
            elif key in ["backup_interval", "auto_save_interval", "editor_font_size"]:
                if not isinstance(value, int) or value <= 0:
                    value = DEFAULT_CONFIG[key]
            # 验证布尔类型
            elif key in ["backup_enabled", "auto_save"]:
                if not isinstance(value, bool):
                    value = DEFAULT_CONFIG[key]
            # 验证嵌套配置
            elif key in ["terminal_colors", "notifications", "greetings"]:
                if isinstance(value, dict):
                    validated[key].update(value)
                continue
            validated[key] = value
    
    return validated

def load_config() -> Dict[str, Any]:
    """加载配置文件"""
    global _config_cache
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # 验证并修复配置
            validated_config = validate_config(config)
            _config_cache = validated_config
            return validated_config
        except json.JSONDecodeError:
            _config_cache = DEFAULT_CONFIG
            return DEFAULT_CONFIG
    _config_cache = DEFAULT_CONFIG
    return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]):
    """保存配置文件"""
    global _config_cache
    # 验证配置后再保存
    validated_config = validate_config(config)
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(validated_config, f, ensure_ascii=False, indent=2)
    _config_cache = validated_config

def get_config() -> Dict[str, Any]:
    """获取配置（带缓存）"""
    global _config_cache
    if _config_cache is None:
        return load_config()
    return _config_cache

def update_config(key: str, value: Any):
    """更新配置"""
    config = get_config()
    config[key] = value
    save_config(config)

def reset_config():
    """重置配置到默认值"""
    global _config_cache
    save_config(DEFAULT_CONFIG)
    _config_cache = DEFAULT_CONFIG
    return DEFAULT_CONFIG
