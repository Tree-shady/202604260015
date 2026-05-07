#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI写作提示系统
提供各种写作主题和提示词
"""

import random
from datetime import datetime, date
from typing import Dict, List

WRITING_PROMPTS = {
    'daily': [
        "今天最让你感恩的三件事是什么？",
        "今天有什么让你感到自豪的成就？",
        "今天你学到了什么新东西？",
        "如果今天重新来过，你会有什么不同？",
        "描述今天你的心情变化历程。",
        "今天和谁的交流让你印象最深？",
        "今天让你最开心的瞬间是什么？",
        "今天你为自己或他人做了什么好事？"
    ],
    'reflection': [
        "回顾过去一周，你最大的收获是什么？",
        "写下三个你今年想实现的目标。",
        "你最想对10年前的自己说什么？",
        "你最想对10年后的自己说什么？",
        "什么事让你感到真正的快乐？",
        "如果可以选择，你想拥有什么超能力？"
    ],
    'creative': [
        "写一个关于今天天气的故事。",
        "用五种感官描述你现在的环境。",
        "假如你是某种动物，会怎样度过这一天？",
        "写一首关于时间的诗。",
        "给未来的自己写一封信。",
        "写一篇只有对话的小故事。"
    ],
    'gratitude': [
        "感谢今天出现在你生命中的一个人。",
        "感谢你拥有的一样东西。",
        "感谢今天学到的一个教训。",
        "感谢你的健康。",
        "感谢一个美好的回忆。"
    ],
    'challenges': [
        "今天遇到的最大挑战是什么？你如何应对的？",
        "有什么事情你今天想做但没完成的？",
        "今天克服了什么困难？"
    ]
}

MOOD_SUGGESTIONS = {
    'excited': [
        "太棒了！今天有什么事让你这么兴奋？",
        "和我分享一下你今天的激动时刻！"
    ],
    'happy': [
        "今天的开心来自哪里？",
        "记录下这份美好的心情！"
    ],
    'neutral': [
        "今天感觉平静，有什么想记录的吗？",
        "普通的一天也值得被记录。"
    ],
    'sad': [
        "允许自己悲伤，把它写下来会好一些。",
        "今天发生了什么让你难过的事？"
    ],
    'frustrated': [
        "是什么让你感到沮丧？写出来会有帮助的。",
        "把你的沮丧倾诉在日记里吧。"
    ]
}

def get_random_prompt(category: str = 'daily') -> str:
    """获取随机写作提示"""
    if category not in WRITING_PROMPTS:
        category = 'daily'
    return random.choice(WRITING_PROMPTS[category])

def get_prompt_by_mood(mood: str) -> str:
    """根据心情获取提示"""
    if mood in MOOD_SUGGESTIONS:
        return random.choice(MOOD_SUGGESTIONS[mood])
    return get_random_prompt()

def get_all_categories() -> List[str]:
    """获取所有提示分类"""
    return list(WRITING_PROMPTS.keys())

def get_prompts_by_category(category: str, count: int = 3) -> List[str]:
    """获取指定分类的多个提示"""
    if category not in WRITING_PROMPTS:
        category = 'daily'
    prompts = WRITING_PROMPTS[category]
    return random.sample(prompts, min(count, len(prompts)))

def get_seasonal_prompt() -> str:
    """获取季节性提示"""
    today = date.today()
    month = today.month
    
    seasonal_prompts = {
        1: ["新年的第一天，写下你的愿望。", "冬日里最温暖的回忆。"],
        2: ["情人节，记录你心中的爱。", "这个春天你有什么期待？"],
        3: ["春天的气息让你想起什么？", "写下一个新开始。"],
        4: ["春天的花朵给你什么启发？", "记录春天的颜色。"],
        5: ["劳动节，你在为什么努力？", "初夏的感觉。"],
        6: ["毕业季，回望过去。", "儿童节，回忆童年。"],
        7: ["夏日最爱的活动是什么？", "记录阳光明媚的一天。"],
        8: ["暑假的美好回忆。", "炙热天气里的清凉时刻。"],
        9: ["开学季，新的目标。", "秋天的颜色。"],
        10: ["万圣节的故事。", "收获的季节，感恩的心情。"],
        11: ["感恩节，感谢生活。", "秋天的落叶。"],
        12: ["圣诞节的愿望。", "年末总结。"]
    }
    
    if month in seasonal_prompts:
        return random.choice(seasonal_prompts[month])
    return get_random_prompt()

def get_time_based_prompt() -> str:
    """根据时间获取提示"""
    hour = datetime.now().hour
    
    if 5 <= hour < 12:
        prompts = [
            "今天早晨你有什么计划？",
            "写下今天的三个目标。",
            "早上好！今天期待什么？"
        ]
    elif 12 <= hour < 18:
        prompts = [
            "今天中午怎么样？",
            "下午你打算做什么？",
            "记录这半天的感受。"
        ]
    else:
        prompts = [
            "今天过得如何？",
            "晚上，回顾这一天。",
            "今天最难忘的事是什么？"
        ]
    return random.choice(prompts)
