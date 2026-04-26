"""
搜索功能模块

提供日记内容搜索功能，支持多关键词搜索和上下文显示
"""

from pathlib import Path
from .config import ENTRIES_DIR

def search_entries(keyword):
    """在日记内容中搜索关键词"""
    entries = ENTRIES_DIR.glob("*.txt")
    results = []
    
    # 支持多关键词（用空格分隔）
    keywords = keyword.split()
    
    for entry in entries:
        date_str = entry.stem
        with open(entry, 'r', encoding='utf-8') as f:
            content = f.read().lower()
            
            # 检查是否包含所有关键词
            if all(k.lower() in content for k in keywords):
                # 查找匹配的行
                lines = content.split('\n')
                matches = []
                for i, line in enumerate(lines):
                    if any(k.lower() in line for k in keywords):
                        # 显示上下文（前后各一行）
                        start = max(0, i-1)
                        end = min(len(lines), i+2)
                        context = lines[start:end]
                        matches.append((i+1, context))
                
                if matches:
                    results.append((date_str, matches))
    
    return results
