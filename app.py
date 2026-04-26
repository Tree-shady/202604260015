from flask import Flask, render_template, request, redirect, url_for, flash
import os
import json
from datetime import datetime
from pathlib import Path

# 配置
ENTRIES_DIR = Path("entries")
DATE_FORMAT = "%Y-%m-%d"
TAGS_FILE = Path("tags.json")

# 确保目录存在
ENTRIES_DIR.mkdir(exist_ok=True)

app = Flask(__name__)
app.secret_key = 'your-secret-key'

# 初始化标签文件
def init_tags_file():
    if not TAGS_FILE.exists():
        with open(TAGS_FILE, 'w', encoding='utf-8') as f:
            json.dump({}, f)

init_tags_file()

def get_tags():
    with open(TAGS_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_tags(tags):
    with open(TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tags, f, ensure_ascii=False, indent=2)

def get_entries():
    return sorted(ENTRIES_DIR.glob("*.txt"), reverse=True)

def get_entry_content(date_str):
    file_path = ENTRIES_DIR / f"{date_str}.txt"
    if file_path.exists():
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取标签和内容
        lines = content.split('\n')
        tags = []
        timestamp = ""
        
        if lines and lines[0].startswith("[") and "]" in lines[0]:
            timestamp = lines[0]
            lines = lines[1:]
        
        if lines and lines[0].startswith("Tags: "):
            tags_str = lines[0][6:]
            tags = [tag.strip() for tag in tags_str.split(',')]
            lines = lines[1:]
        
        content = '\n'.join(lines)
        return timestamp, tags, content
    return None, [], ""

def get_calendar_data(year, month):
    """获取日历数据"""
    from calendar import monthrange, weekday
    
    # 获取月份的天数和第一天是星期几
    days_in_month = monthrange(year, month)[1]
    first_day_weekday = weekday(year, month, 1)  # 0=Monday, 6=Sunday
    
    # 调整为 0=Sunday, 6=Saturday
    first_day_weekday = (first_day_weekday + 1) % 7
    
    # 生成日历数据
    calendar_days = []
    
    # 添加上个月的填充天数
    prev_month_days = first_day_weekday
    if prev_month_days > 0:
        prev_year, prev_month = (year, month-1) if month > 1 else (year-1, 12)
        prev_month_days_total = monthrange(prev_year, prev_month)[1]
        for day in range(prev_month_days_total - prev_month_days + 1, prev_month_days_total + 1):
            calendar_days.append({
                'day': day,
                'month': prev_month,
                'year': prev_year,
                'is_other_month': True,
                'has_entry': False
            })
    
    # 添加当前月的天数
    today = datetime.now()
    current_year = today.year
    current_month = today.month
    current_day = today.day
    
    for day in range(1, days_in_month + 1):
        date_str = f"{year:04d}-{month:02d}-{day:02d}"
        file_path = ENTRIES_DIR / f"{date_str}.txt"
        is_today = (year == current_year and month == current_month and day == current_day)
        
        calendar_days.append({
            'day': day,
            'month': month,
            'year': year,
            'is_other_month': False,
            'is_today': is_today,
            'has_entry': file_path.exists(),
            'date_str': date_str
        })
    
    # 添加下个月的填充天数
    total_days = len(calendar_days)
    remaining_days = (7 - (total_days % 7)) % 7
    if remaining_days > 0:
        next_year, next_month = (year, month+1) if month < 12 else (year+1, 1)
        for day in range(1, remaining_days + 1):
            calendar_days.append({
                'day': day,
                'month': next_month,
                'year': next_year,
                'is_other_month': True,
                'has_entry': False
            })
    
    return calendar_days

def get_stats():
    """获取统计数据"""
    entries = get_entries()
    total_entries = len(entries)
    
    # 计算总字数
    total_words = 0
    total_chars = 0
    
    for entry in entries:
        with open(entry, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.split('\n')
            # 移除时间戳和标签行
            if lines and lines[0].startswith("[") and "]" in lines[0]:
                lines = lines[1:]
            if lines and lines[0].startswith("Tags: "):
                lines = lines[1:]
            content = '\n'.join(lines)
            total_chars += len(content)
            total_words += len(content.split())
    
    # 获取标签统计
    tag_data = get_tags()
    total_tags = len(tag_data)
    
    return {
        'total_entries': total_entries,
        'total_words': total_words,
        'total_chars': total_chars,
        'total_tags': total_tags
    }

@app.route('/')
def index():
    today = datetime.now()
    year = today.year
    month = today.month
    
    entries = get_entries()
    tag_data = get_tags()
    calendar_data = get_calendar_data(year, month)
    stats = get_stats()
    
    return render_template('index.html', 
                         entries=entries, 
                         tags=tag_data, 
                         calendar_data=calendar_data,
                         current_year=year,
                         current_month=month,
                         stats=stats)

@app.route('/new', methods=['GET', 'POST'])
def new_entry():
    if request.method == 'POST':
        date_str = request.form['date']
        tags_str = request.form['tags']
        content = request.form['content']
        
        if not date_str or not content:
            flash('日期和内容不能为空', 'danger')
            return redirect(url_for('new_entry'))
        
        try:
            datetime.strptime(date_str, DATE_FORMAT)
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式', 'danger')
            return redirect(url_for('new_entry'))
        
        # 保存日记
        file_path = ENTRIES_DIR / f"{date_str}.txt"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = f"[{timestamp}]\n"
        if tags_str:
            full_content += f"Tags: {tags_str}\n"
        full_content += content
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # 更新标签索引
        if tags_str:
            tags = [tag.strip() for tag in tags_str.split(',')]
            tag_data = get_tags()
            
            # 移除旧标签关联
            for tag, dates in tag_data.items():
                if date_str in dates:
                    dates.remove(date_str)
                    if not dates:
                        del tag_data[tag]
            
            # 添加新标签关联
            for tag in tags:
                if tag not in tag_data:
                    tag_data[tag] = []
                if date_str not in tag_data[tag]:
                    tag_data[tag].append(date_str)
            
            save_tags(tag_data)
        
        flash('日记已保存', 'success')
        return redirect(url_for('index'))
    
    return render_template('new.html', current_date=datetime.now().strftime(DATE_FORMAT))

@app.route('/entry/<date_str>')
def view_entry(date_str):
    timestamp, tags, content = get_entry_content(date_str)
    if content:
        return render_template('view.html', date_str=date_str, timestamp=timestamp, tags=tags, content=content)
    flash('未找到该日记', 'danger')
    return redirect(url_for('index'))

@app.route('/edit/<date_str>', methods=['GET', 'POST'])
def edit_entry(date_str):
    timestamp, tags, content = get_entry_content(date_str)
    if not content:
        flash('未找到该日记', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        new_date = request.form['date']
        tags_str = request.form['tags']
        new_content = request.form['content']
        
        if not new_date or not new_content:
            flash('日期和内容不能为空', 'danger')
            return redirect(url_for('edit_entry', date_str=date_str))
        
        try:
            datetime.strptime(new_date, DATE_FORMAT)
        except ValueError:
            flash('日期格式错误，请使用 YYYY-MM-DD 格式', 'danger')
            return redirect(url_for('edit_entry', date_str=date_str))
        
        # 如果日期改变，需要处理文件重命名
        if new_date != date_str:
            old_path = ENTRIES_DIR / f"{date_str}.txt"
            new_path = ENTRIES_DIR / f"{new_date}.txt"
            if old_path.exists():
                old_path.rename(new_path)
        
        # 保存日记
        file_path = ENTRIES_DIR / f"{new_date}.txt"
        new_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = f"[{new_timestamp}]\n"
        if tags_str:
            full_content += f"Tags: {tags_str}\n"
        full_content += new_content
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        # 更新标签索引
        if tags_str:
            tags_list = [tag.strip() for tag in tags_str.split(',')]
            tag_data = get_tags()
            
            # 移除旧日期的标签关联
            for tag, dates in tag_data.items():
                if date_str in dates:
                    dates.remove(date_str)
                    if not dates:
                        del tag_data[tag]
            
            # 添加新日期的标签关联
            for tag in tags_list:
                if tag not in tag_data:
                    tag_data[tag] = []
                if new_date not in tag_data[tag]:
                    tag_data[tag].append(new_date)
            
            save_tags(tag_data)
        
        flash('日记已更新', 'success')
        return redirect(url_for('view_entry', date_str=new_date))
    
    return render_template('edit.html', date_str=date_str, tags=tags, content=content)

@app.route('/delete/<date_str>', methods=['POST'])
def delete_entry(date_str):
    file_path = ENTRIES_DIR / f"{date_str}.txt"
    if file_path.exists():
        file_path.unlink()
        
        # 更新标签索引
        tag_data = get_tags()
        for tag, dates in tag_data.items():
            if date_str in dates:
                dates.remove(date_str)
                if not dates:
                    del tag_data[tag]
        save_tags(tag_data)
        
        flash('日记已删除', 'success')
    else:
        flash('未找到该日记', 'danger')
    return redirect(url_for('index'))

@app.route('/tag/<tag>')
def view_tag(tag):
    tag_data = get_tags()
    if tag in tag_data:
        dates = tag_data[tag]
        entries = []
        for date_str in dates:
            file_path = ENTRIES_DIR / f"{date_str}.txt"
            if file_path.exists():
                entries.append(file_path)
        return render_template('tag.html', tag=tag, entries=entries)
    flash('未找到该标签', 'danger')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
