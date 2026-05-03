"""
问候语模块

提供每日问候语功能，支持本地随机和在线API获取
"""

import random
import requests
from datetime import datetime
from .config import get_config

# 本地问候语库
LOCAL_GREETINGS = [
    {
        "text": "新的一天开始了，愿你充满活力！",
        "author": ""
    },
    {
        "text": "每一个不曾起舞的日子，都是对生命的辜负。",
        "author": "尼采"
    },
    {
        "text": "生活不是等待暴风雨过去，而是学会在雨中跳舞。",
        "author": ""
    },
    {
        "text": "今天也要元气满满地度过呀！",
        "author": ""
    },
    {
        "text": "愿你今天的心情像阳光一样明媚。",
        "author": ""
    },
    {
        "text": "生活明朗，万物可爱，人间值得，未来可期。",
        "author": ""
    },
    {
        "text": "做你自己，因为别人都有人做了。",
        "author": "王尔德"
    },
    {
        "text": "成功不是终点，失败也不是终结，只有勇气才是永恒。",
        "author": "温斯顿·丘吉尔"
    },
    {
        "text": "你的时间有限，不要浪费时间活在别人的生活里。",
        "author": "史蒂夫·乔布斯"
    },
    {
        "text": "人生就像一盒巧克力，你永远不知道下一颗是什么味道。",
        "author": "阿甘正传"
    },
    {
        "text": "坚持自己的梦想，即使没有翅膀也能飞翔。",
        "author": ""
    },
    {
        "text": "把每一天都当成生命中的最后一天去过。",
        "author": ""
    },
    {
        "text": "快乐不是因为拥有的多，而是计较的少。",
        "author": ""
    },
    {
        "text": "相信自己，你比想象中更强大。",
        "author": ""
    },
    {
        "text": "今天的努力是明天的铺垫。",
        "author": ""
    }
]

# 常用API（部分可能需要密钥，这里用免费公开的）
API_SOURCES = [
    # 一言API - 免费，无需密钥
    {
        "name": "hitokoto",
        "url": "https://v1.hitokoto.cn/",
        "method": "GET",
        "params": {},
        "extract_text": lambda data: data.get('hitokoto', ''),
        "extract_author": lambda data: data.get('from', '')
    },
    # 每日一句英语名言
    {
        "name": "quotable",
        "url": "https://api.quotable.io/random",
        "method": "GET",
        "params": {},
        "extract_text": lambda data: data.get('content', ''),
        "extract_author": lambda data: data.get('author', '')
    }
]

def get_local_greeting():
    """
    获取本地随机问候语
    
    Returns:
        dict: 包含 text 和 author 的问候语
    """
    return random.choice(LOCAL_GREETINGS)

def get_api_greeting(source_index=0):
    """
    从API获取问候语
    
    Args:
        source_index: API源索引
        
    Returns:
        dict: 包含 text 和 author 的问候语，如果失败返回None
    """
    if source_index < 0 or source_index >= len(API_SOURCES):
        source_index = 0
    
    source = API_SOURCES[source_index]
    
    try:
        response = requests.get(
            source["url"],
            params=source["params"],
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return {
                "text": source["extract_text"](data),
                "author": source["extract_author"](data)
            }
    except Exception as e:
        print(f"API问候语获取失败: {e}")
    
    return None

def get_greeting():
    """
    获取问候语（根据配置选择来源）
    
    Returns:
        dict: 包含 text 和 author 的问候语
    """
    config = get_config()
    greetings_config = config.get('greetings', {})
    
    if not greetings_config.get('enabled', True):
        return get_local_greeting()
    
    source = greetings_config.get('source', 'local')
    
    if source == 'api':
        # 尝试从API获取，失败则回退到本地
        greeting = get_api_greeting()
        if greeting and greeting.get('text'):
            return greeting
    
    # 默认使用本地
    return get_local_greeting()

def format_greeting(greeting):
    """
    格式化问候语
    
    Args:
        greeting: 问候语字典
        
    Returns:
        str: 格式化后的问候语
    """
    text = greeting.get('text', '')
    author = greeting.get('author', '')
    
    if author:
        return f'"{text}" — {author}'
    return text

def get_time_based_greeting():
    """
    根据时间获取问候语
    
    Returns:
        str: 时间相关的问候
    """
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        return "早上好！"
    elif 12 <= hour < 18:
        return "下午好！"
    elif 18 <= hour < 22:
        return "晚上好！"
    else:
        return "夜深了，注意休息！"

def get_combined_greeting():
    """
    获取组合问候语（时间问候 + 每日一句）
    
    Returns:
        dict: 包含 time_greeting 和 daily_greeting 的字典
    """
    return {
        "time_greeting": get_time_based_greeting(),
        "daily_greeting": get_greeting()
    }
