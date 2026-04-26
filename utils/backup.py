import shutil
from datetime import datetime
from pathlib import Path
from .config import ENTRIES_DIR

def backup_entries():
    """备份 entries 文件夹"""
    if not ENTRIES_DIR.exists() or not any(ENTRIES_DIR.iterdir()):
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"entries_backup_{timestamp}")
    shutil.copytree(ENTRIES_DIR, backup_dir)
    return backup_dir

def list_backups():
    """列出所有备份"""
    backups = []
    for item in Path(".").glob("entries_backup_*"):
        if item.is_dir():
            # 提取时间戳
            timestamp_str = item.name.replace("entries_backup_", "")
            try:
                timestamp = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S")
                backups.append((timestamp, item))
            except ValueError:
                pass
    
    # 按时间排序（最新的在前）
    backups.sort(reverse=True, key=lambda x: x[0])
    return backups

def restore_backup(backup_dir):
    """恢复备份"""
    if not backup_dir.exists():
        return False
    
    # 清空当前 entries 目录
    for file in ENTRIES_DIR.glob("*"):
        if file.is_file():
            file.unlink()
    
    # 复制备份文件
    for file in backup_dir.glob("*"):
        if file.is_file():
            shutil.copy(file, ENTRIES_DIR)
    
    return True

def delete_backup(backup_dir):
    """删除备份"""
    if not backup_dir.exists():
        return False
    
    shutil.rmtree(backup_dir)
    return True
