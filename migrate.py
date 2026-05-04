#!/usr/bin/env python3
"""
数据库迁移脚本
为现有数据库添加新的用户字段
"""
import sqlite3
import os
from pathlib import Path
from datetime import datetime

def main():
    db_path = Path("diary.db")
    
    if not db_path.exists():
        print("数据库文件不存在，跳过迁移")
        return
    
    print(f"正在更新数据库: {db_path}")
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    try:
        # 检查并添加新字段
        cursor.execute("PRAGMA table_info(users)")
        columns = [col[1] for col in cursor.fetchall()]
        
        new_fields = [
            ("current_streak", "INTEGER DEFAULT 0"),
            ("longest_streak", "INTEGER DEFAULT 0"),
            ("last_entry_date", "TEXT"),
            ("total_entries", "INTEGER DEFAULT 0")
        ]
        
        for field_name, field_def in new_fields:
            if field_name not in columns:
                print(f"  添加字段: {field_name}")
                cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_def}")
        
        conn.commit()
        
        # 更新现有用户的统计数据
        print("\n正在更新用户统计数据...")
        cursor.execute("SELECT id FROM users")
        user_ids = [row[0] for row in cursor.fetchall()]
        
        for user_id in user_ids:
            # 获取用户有日记的日期
            cursor.execute("""
                SELECT DISTINCT date_str 
                FROM entries 
                WHERE user_id = ? 
                ORDER BY date_str
            """, (user_id,))
            dates = [row[0] for row in cursor.fetchall()]
            
            if dates:
                total_entries = len(dates)
                last_entry_date = max(dates)
                
                # 计算连续打卡天数
                current_streak = calculate_current_streak(dates)
                longest_streak = calculate_longest_streak(dates)
                
                cursor.execute("""
                    UPDATE users 
                    SET current_streak = ?, 
                        longest_streak = ?, 
                        last_entry_date = ?, 
                        total_entries = ?
                    WHERE id = ?
                """, (current_streak, longest_streak, last_entry_date, total_entries, user_id))
                
                print(f"  用户 {user_id}: {current_streak} 天连续, {total_entries} 篇日记")
            else:
                print(f"  用户 {user_id}: 无日记")
        
        conn.commit()
        print("\n数据库更新完成！")
        
    except Exception as e:
        print(f"错误: {e}")
        conn.rollback()
    finally:
        conn.close()

def calculate_current_streak(dates):
    """计算当前连续打卡天数"""
    from datetime import datetime, timedelta
    
    if not dates:
        return 0
    
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    sorted_dates = sorted(dates, reverse=True)
    
    streak = 0
    current_date = None
    
    if today in sorted_dates:
        current_date = today
        streak = 1
    elif yesterday in sorted_dates:
        current_date = yesterday
        streak = 1
    else:
        return 0
    
    for date in sorted_dates:
        if date == current_date:
            continue
        
        try:
            d1 = datetime.strptime(current_date, "%Y-%m-%d")
            d2 = datetime.strptime(date, "%Y-%m-%d")
            delta = d1 - d2
            if delta.days == 1:
                streak += 1
                current_date = date
            else:
                break
        except:
            break
    
    return streak

def calculate_longest_streak(dates):
    """计算最长连续打卡天数"""
    from datetime import datetime
    
    if not dates:
        return 0
    
    sorted_dates = sorted(dates)
    longest = 1
    current = 1
    
    for i in range(1, len(sorted_dates)):
        try:
            d1 = datetime.strptime(sorted_dates[i], "%Y-%m-%d")
            d2 = datetime.strptime(sorted_dates[i-1], "%Y-%m-%d")
            delta = d1 - d2
            if delta.days == 1:
                current += 1
                if current > longest:
                    longest = current
            else:
                current = 1
        except:
            current = 1
    
    return longest

if __name__ == "__main__":
    main()
