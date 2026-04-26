"""
日记模板模块

提供各种日记模板功能
"""

from datetime import datetime

# 定义日记模板
TEMPLATES = {
    'daily': {
        'name': '日常日记',
        'description': '记录每天的生活点滴',
        'content': '''# 今日记录

## 今日心情

## 今日事件
- 
- 
- 

## 今日感悟

## 明日计划
- 
- 
- 
'''
    },
    'work': {
        'name': '工作日记',
        'description': '记录工作内容和进展',
        'content': '''# 工作日志

## 今日任务
- [ ] 
- [ ] 
- [ ] 

## 完成情况
- [x] 
- [x] 
- [x] 

## 遇到的问题

## 解决方法

## 明日计划
- 
- 
- 
'''
    },
    'study': {
        'name': '学习笔记',
        'description': '记录学习内容和收获',
        'content': '''# 学习笔记

## 学习内容

## 重点难点

## 学习收获

## 疑问和思考

## 下一步计划
'''
    },
    'travel': {
        'name': '旅行日记',
        'description': '记录旅行中的见闻和感受',
        'content': '''# 旅行日记

## 日期和地点

## 今日行程
- 
- 
- 

## 所见所闻

## 美食推荐

## 心情感受

## 明日安排
'''
    },
    'health': {
        'name': '健康日记',
        'description': '记录健康状况和运动情况',
        'content': '''# 健康日记

## 今日身体状况
- 体重: 
- 血压: 
- 睡眠: 

## 今日运动
- 类型: 
- 时长: 
- 强度: 

## 今日饮食
- 早餐: 
- 午餐: 
- 晚餐: 

## 今日感受

## 健康目标
'''
    },
    'gratitude': {
        'name': '感恩日记',
        'description': '记录每天的感恩事项',
        'content': '''# 感恩日记

## 今日感恩
1. 
2. 
3. 

## 今日收获

## 今日成长

## 明日期待
'''
    },
    'dream': {
        'name': '梦境记录',
        'description': '记录梦境内容',
        'content': '''# 梦境记录

## 日期
{{ date }}

## 梦境内容

## 梦中感受

## 醒后思考

## 可能的含义
'''
    },
    'project': {
        'name': '项目计划',
        'description': '记录项目进展和计划',
        'content': '''# 项目计划

## 项目名称

## 当前进展

## 下一步计划
- 
- 
- 

## 遇到的问题

## 解决方案

## 时间节点
'''
    }
}

def get_template(template_id):
    """获取指定模板
    
    Args:
        template_id: 模板ID
    
    Returns:
        dict: 模板数据
    """
    return TEMPLATES.get(template_id, TEMPLATES['daily'])

def get_all_templates():
    """获取所有模板
    
    Returns:
        dict: 所有模板数据
    """
    return TEMPLATES

def render_template(template_id, date_str=None):
    """渲染模板内容，替换变量
    
    Args:
        template_id: 模板ID
        date_str: 日期字符串
    
    Returns:
        str: 渲染后的模板内容
    """
    template = get_template(template_id)
    content = template['content']
    
    # 替换变量
    if date_str:
        content = content.replace('{{ date }}', date_str)
    else:
        content = content.replace('{{ date }}', datetime.now().strftime('%Y-%m-%d'))
    
    return content
