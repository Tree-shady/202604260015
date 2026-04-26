"""
数据导入/导出模块

提供日记数据的导入和导出功能
"""

import json
import csv
import zipfile
from pathlib import Path
from datetime import datetime
from .storage import get_entries, get_entry_content, get_tags, save_tags, update_tags_index
from .config import ENTRIES_DIR, TAGS_FILE, DATE_FORMAT

def export_to_json(output_file=None):
    """导出日记数据到 JSON 文件
    
    Args:
        output_file: 输出文件路径，默认生成 timestamp-based 文件名
    
    Returns:
        Path: 导出文件的路径
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"diary_export_{timestamp}.json"
    
    output_path = Path(output_file)
    
    # 收集数据
    data = {
        'export_date': datetime.now().isoformat(),
        'diaries': [],
        'tags': get_tags()
    }
    
    # 导出日记
    entries = get_entries()
    for entry in entries:
        date_str = entry.stem
        timestamp, tags, content = get_entry_content(date_str)
        
        data['diaries'].append({
            'date': date_str,
            'timestamp': timestamp,
            'tags': tags,
            'content': content
        })
    
    # 保存到文件
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return output_path

def export_to_csv(output_file=None):
    """导出日记数据到 CSV 文件
    
    Args:
        output_file: 输出文件路径，默认生成 timestamp-based 文件名
    
    Returns:
        Path: 导出文件的路径
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"diary_export_{timestamp}.csv"
    
    output_path = Path(output_file)
    
    # 写入 CSV
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Timestamp', 'Tags', 'Content'])
        
        entries = get_entries()
        for entry in entries:
            date_str = entry.stem
            timestamp, tags, content = get_entry_content(date_str)
            tags_str = ', '.join(tags)
            writer.writerow([date_str, timestamp, tags_str, content])
    
    return output_path

def export_to_markdown(output_dir=None):
    """导出日记数据到 Markdown 文件（每个日记一个文件）
    
    Args:
        output_dir: 输出目录，默认生成 timestamp-based 目录名
    
    Returns:
        Path: 导出目录的路径
    """
    if output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = f"diary_export_{timestamp}"
    
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    entries = get_entries()
    for entry in entries:
        date_str = entry.stem
        timestamp, tags, content = get_entry_content(date_str)
        
        # 创建 Markdown 文件
        md_file = output_path / f"{date_str}.md"
        with open(md_file, 'w', encoding='utf-8') as f:
            f.write(f"# {date_str} 的日记\n\n")
            if timestamp:
                f.write(f"**时间：** {timestamp}\n\n")
            if tags:
                f.write(f"**标签：** {', '.join(tags)}\n\n")
            f.write(content)
    
    return output_path

def export_to_zip(output_file=None):
    """导出日记数据到 ZIP 文件（包含所有日记和标签）
    
    Args:
        output_file: 输出文件路径，默认生成 timestamp-based 文件名
    
    Returns:
        Path: 导出文件的路径
    """
    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"diary_export_{timestamp}.zip"
    
    output_path = Path(output_file)
    
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        # 导出标签文件
        with open(TAGS_FILE, 'r', encoding='utf-8') as f:
            tags_content = f.read()
        zf.writestr('tags.json', tags_content)
        
        # 导出日记文件
        entries = get_entries()
        for entry in entries:
            date_str = entry.stem
            with open(entry, 'r', encoding='utf-8') as f:
                content = f.read()
            zf.writestr(f'entries/{date_str}.txt', content)
    
    return output_path

def import_from_json(input_file):
    """从 JSON 文件导入日记数据
    
    Args:
        input_file: 输入 JSON 文件路径
    
    Returns:
        dict: 导入结果，包含成功和失败的数量
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_file}")
    
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    success_count = 0
    failed_count = 0
    
    # 导入日记
    diaries = data.get('diaries', [])
    for diary in diaries:
        date_str = diary.get('date')
        content = diary.get('content', '')
        tags = diary.get('tags', [])
        
        if not date_str or not content:
            failed_count += 1
            continue
        
        try:
            # 验证日期格式
            datetime.strptime(date_str, DATE_FORMAT)
            
            # 保存日记
            file_path = ENTRIES_DIR / f"{date_str}.txt"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            full_content = f"[{timestamp}]\n"
            if tags:
                full_content += f"Tags: {', '.join(tags)}\n"
            full_content += content
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            # 更新标签索引
            update_tags_index(date_str, tags)
            success_count += 1
        except Exception:
            failed_count += 1
    
    # 导入标签
    if 'tags' in data:
        try:
            save_tags(data['tags'])
        except Exception:
            pass
    
    return {
        'success': success_count,
        'failed': failed_count
    }

def import_from_zip(input_file):
    """从 ZIP 文件导入日记数据
    
    Args:
        input_file: 输入 ZIP 文件路径
    
    Returns:
        dict: 导入结果，包含成功和失败的数量
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_file}")
    
    success_count = 0
    failed_count = 0
    
    with zipfile.ZipFile(input_path, 'r') as zf:
        # 导入标签文件
        if 'tags.json' in zf.namelist():
            try:
                with zf.open('tags.json') as f:
                    tags_content = f.read().decode('utf-8')
                    tags_data = json.loads(tags_content)
                    save_tags(tags_data)
            except Exception:
                pass
        
        # 导入日记文件
        for name in zf.namelist():
            if name.startswith('entries/') and name.endswith('.txt'):
                try:
                    date_str = Path(name).stem
                    
                    # 验证日期格式
                    datetime.strptime(date_str, DATE_FORMAT)
                    
                    # 保存日记
                    file_path = ENTRIES_DIR / f"{date_str}.txt"
                    with zf.open(name) as f:
                        content = f.read().decode('utf-8')
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    success_count += 1
                except Exception:
                    failed_count += 1
    
    return {
        'success': success_count,
        'failed': failed_count
    }

def import_from_directory(input_dir):
    """从目录导入日记数据（支持 .txt 和 .md 文件）
    
    Args:
        input_dir: 输入目录路径
    
    Returns:
        dict: 导入结果，包含成功和失败的数量
    """
    input_path = Path(input_dir)
    if not input_path.exists() or not input_path.is_dir():
        raise FileNotFoundError(f"目录不存在: {input_dir}")
    
    success_count = 0
    failed_count = 0
    
    # 导入 .txt 和 .md 文件
    for file in input_path.glob("*.txt"):
        try:
            date_str = file.stem
            
            # 验证日期格式
            datetime.strptime(date_str, DATE_FORMAT)
            
            # 复制文件
            file_path = ENTRIES_DIR / f"{date_str}.txt"
            file_path.write_text(file.read_text(encoding='utf-8'), encoding='utf-8')
            
            success_count += 1
        except Exception:
            failed_count += 1
    
    for file in input_path.glob("*.md"):
        try:
            date_str = file.stem
            
            # 验证日期格式
            datetime.strptime(date_str, DATE_FORMAT)
            
            # 转换为 txt 格式
            content = file.read_text(encoding='utf-8')
            file_path = ENTRIES_DIR / f"{date_str}.txt"
            file_path.write_text(content, encoding='utf-8')
            
            success_count += 1
        except Exception:
            failed_count += 1
    
    return {
        'success': success_count,
        'failed': failed_count
    }
