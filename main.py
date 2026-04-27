import sys
import os
import json
from datetime import datetime
from pathlib import Path
import markdown
from colorama import init, Fore, Style

from utils.config import ENTRIES_DIR, DATE_FORMAT, TAGS_FILE
from utils.storage import ensure_dir, get_today_str, get_file_path, get_tags, save_tags, update_tags_index
from utils.backup import backup_entries as backup_entries_util, list_backups as list_backups_util, restore_backup as restore_backup_util, delete_backup as delete_backup_util
from utils.search import search_entries as search_entries_util
from utils.stats import get_diary_stats, get_tag_stats, parse_relative_date, export_diary, export_all_diaries
from utils.notification import show_notification
from utils.settings import show_settings

init(autoreset=True)

# 颜色配置（与Web版保持一致）
PRIMARY_COLOR = Fore.GREEN      # #10b981
SECONDARY_COLOR = Fore.CYAN      # #64748b
ACCENT_COLOR = Fore.YELLOW       # #f59e0b
TEXT_COLOR = Fore.WHITE          # #1e293b
MUTED_COLOR = Fore.LIGHTBLACK_EX # #64748b
ERROR_COLOR = Fore.RED           # #ef4444
SUCCESS_COLOR = Fore.GREEN       # #10b981
INFO_COLOR = Fore.BLUE           # #3b82f6


def write_entry(content, date_str=None, tags_str=None):
    """写日记（默认今天）"""
    if date_str is None:
        date_str = get_today_str()

    file_path = get_file_path(date_str)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # 构建内容（包含标签）
    full_content = f"[{timestamp}]\n"
    if tags_str:
        full_content += f"Tags: {tags_str}\n"
    full_content += content

    if file_path.exists():
        confirm = input(f"{ACCENT_COLOR}{date_str} 已有日记，是否覆盖？(y/n): ")
        if confirm.lower() != 'y':
            print(f"{ERROR_COLOR}已取消写入")
            return

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    # 更新标签索引
    if tags_str:
        tags = [tag.strip() for tag in tags_str.split(',')]
        update_tags_index(date_str, tags)
    
    print(f"{SUCCESS_COLOR}日记已保存至 {file_path}")

def read_entry(date_str):
    """读取指定日期的日记"""
    file_path = get_file_path(date_str)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"\n{SECONDARY_COLOR}{'=' * 40}")
        print(f"{SECONDARY_COLOR}        {date_str} 的日记")
        print(f"{SECONDARY_COLOR}{'=' * 40}")

        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                print(f"{PRIMARY_COLOR}{Style.BRIGHT}{line[2:]}")
            elif line.startswith('## '):
                print(f"{PRIMARY_COLOR}{line[3:]}")
            elif line.startswith('### '):
                print(f"{SECONDARY_COLOR}{line[4:]}")
            elif line.startswith('**') and line.endswith('**'):
                print(f"{ACCENT_COLOR}{Style.BRIGHT}{line[2:-2]}")
            elif line.startswith('*') and line.endswith('*'):
                print(f"{INFO_COLOR}{line[1:-1]}")
            elif line.startswith('- ') or line.startswith('* '):
                print(f"{TEXT_COLOR}  {ACCENT_COLOR}•{TEXT_COLOR} {line[2:]}")
            elif line.startswith('> '):
                print(f"{INFO_COLOR}  │ {line[2:]}")
            elif line.strip():
                print(f"{TEXT_COLOR}{line}")
            else:
                print()
    except FileNotFoundError:
        print(f"{ERROR_COLOR}未找到 {date_str} 的日记")

def list_entries():
    """列出所有日记的日期"""
    entries = sorted(ENTRIES_DIR.glob("*.txt"))
    if not entries:
        print(f"{ACCENT_COLOR}暂无日记")
        return

    print(f"\n{PRIMARY_COLOR}已有日记：")
    for idx, entry in enumerate(entries, 1):
        date_str = entry.stem
        size = entry.stat().st_size
        print(f"  {SECONDARY_COLOR}{idx}.{TEXT_COLOR} {date_str} {Style.DIM}({size} 字节){Style.RESET_ALL}")

def search_entries(keyword):
    """在日记内容中搜索关键词"""
    results = search_entries_util(keyword)
    if results:
        print(f"\n{PRIMARY_COLOR}找到包含 '{keyword}' 的日记：")
        for date_str, matches in results:
            print(f"\n  {SECONDARY_COLOR}•{TEXT_COLOR} {date_str}")
            for line_num, context in matches:
                print(f"    {ACCENT_COLOR}第 {line_num} 行:")
                for i, line in enumerate(context):
                    if i == 1:  # 匹配的行
                        print(f"      {PRIMARY_COLOR}{line.strip()}")
                    else:  # 上下文行
                        print(f"      {TEXT_COLOR}{line.strip()}")
    else:
        print(f"{ACCENT_COLOR}未找到包含 '{keyword}' 的日记")

def validate_date_str(date_str):
    """验证日期字符串"""
    import re
    # 验证日期格式：YYYY-MM-DD
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        return False
    # 验证日期是否有效
    try:
        datetime.strptime(date_str, DATE_FORMAT)
        return True
    except ValueError:
        return False

def delete_entry(date_str):
    """删除指定日期的日记"""
    # 验证日期字符串
    if not validate_date_str(date_str):
        print(f"{ERROR_COLOR}无效的日期格式")
        return
        
    file_path = get_file_path(date_str)

    if not file_path.exists():
        print(f"{ERROR_COLOR}未找到 {date_str} 的日记")
        return

    confirm = input(f"{ERROR_COLOR}确认删除 {date_str} 的日记？(y/n): ")
    if confirm.lower() == 'y':
        file_path.unlink()
        
        # 更新标签索引
        tag_data = get_tags()
        for tag, dates in tag_data.items():
            if date_str in dates:
                dates.remove(date_str)
                if not dates:
                    del tag_data[tag]
        save_tags(tag_data)
        
        print(f"{SUCCESS_COLOR}已删除 {date_str} 的日记")
    else:
        print(f"{ACCENT_COLOR}已取消删除")

def edit_entry(date_str):
    """编辑已存在的日记"""
    # 验证日期字符串
    if not validate_date_str(date_str):
        print(f"{ERROR_COLOR}无效的日期格式")
        return
        
    file_path = get_file_path(date_str)

    if not file_path.exists():
        print(f"{ERROR_COLOR}未找到 {date_str} 的日记")
        return

    # 读取现有内容
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 提取标签和内容
    lines = content.split('\n')
    tags_str = ""
    timestamp = ""
    
    if lines and lines[0].startswith("[") and "]" in lines[0]:
        timestamp = lines[0]
        lines = lines[1:]
    
    if lines and lines[0].startswith("Tags: "):
        tags_str = lines[0][6:]
        lines = lines[1:]
    
    existing_content = '\n'.join(lines)

    # 显示现有内容
    print(f"\n{SECONDARY_COLOR}【编辑日记 - {date_str}】")
    print(f"{TEXT_COLOR}现有标签: {tags_str or '无'}")
    print(f"{TEXT_COLOR}现有内容:")
    print(f"{TEXT_COLOR}{existing_content}")
    print(f"{TEXT_COLOR}（输入新内容，结束后输入 .end 并回车）")

    # 输入新标签
    new_tags_str = input(f"{TEXT_COLOR}请输入新标签（用逗号分隔多个标签，回车保持原有标签）: ").strip()
    if not new_tags_str:
        new_tags_str = tags_str

    # 输入新内容
    lines = []
    while True:
        line = input()
        if line == ".end":
            break
        lines.append(line)
    new_content = "\n".join(lines)

    if new_content.strip():
        # 构建新内容
        new_timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_content = f"[{new_timestamp}]\n"
        if new_tags_str:
            full_content += f"Tags: {new_tags_str}\n"
        full_content += new_content

        # 保存更新
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)

        # 更新标签索引
        if new_tags_str:
            tags = [tag.strip() for tag in new_tags_str.split(',')]
            update_tags_index(date_str, tags)

        print(f"{SUCCESS_COLOR}日记已更新")
    else:
        print(f"{ERROR_COLOR}内容为空，未更新")

def show_tags():
    """显示所有标签"""
    tag_data = get_tags()
    if not tag_data:
        print(f"{ACCENT_COLOR}暂无标签")
        return
    
    print(f"\n{PRIMARY_COLOR}所有标签：")
    for tag, dates in tag_data.items():
        print(f"  {SECONDARY_COLOR}{tag}{TEXT_COLOR} ({len(dates)} 篇日记)")

def backup_entries():
    """备份 entries 文件夹"""
    backup_dir = backup_entries_util()
    if backup_dir:
        print(f"{SUCCESS_COLOR}日记已备份至 {backup_dir}")

def list_backups():
    """列出所有备份"""
    backups = list_backups_util()
    if not backups:
        print(f"{ACCENT_COLOR}暂无备份")
        return
    
    print(f"\n{PRIMARY_COLOR}所有备份：")
    for idx, (timestamp, backup_dir) in enumerate(backups, 1):
        # 计算备份大小
        size = sum(f.stat().st_size for f in backup_dir.rglob("*"))
        print(f"  {SECONDARY_COLOR}{idx}.{TEXT_COLOR} {timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({size} 字节) - {backup_dir.name}")
    
    return backups

def restore_backup(backup_dir):
    """恢复备份"""
    if not backup_dir.exists():
        print(f"{ERROR_COLOR}备份目录不存在")
        return
    
    # 确认恢复
    confirm = input(f"{ERROR_COLOR}确认恢复备份 {backup_dir.name} 吗？这将覆盖当前的日记！(y/n): ")
    if confirm.lower() != 'y':
        print(f"{ACCENT_COLOR}已取消恢复")
        return
    
    success = restore_backup_util(backup_dir)
    if success:
        print(f"{SUCCESS_COLOR}备份已恢复")

def delete_backup(backup_dir):
    """删除备份"""
    if not backup_dir.exists():
        print(f"{ERROR_COLOR}备份目录不存在")
        return
    
    confirm = input(f"{ERROR_COLOR}确认删除备份 {backup_dir.name} 吗？(y/n): ")
    if confirm.lower() == 'y':
        success = delete_backup_util(backup_dir)
        if success:
            print(f"{SUCCESS_COLOR}备份已删除")
    else:
        print(f"{ACCENT_COLOR}已取消删除")

def backup_management():
    """备份管理"""
    while True:
        print(f"\n{SECONDARY_COLOR}{'=' * 40}")
        print(f"{PRIMARY_COLOR}{Style.BRIGHT}        备份管理")
        print(f"{SECONDARY_COLOR}{'=' * 40}")
        print(f"{TEXT_COLOR}1. 列出所有备份")
        print(f"{TEXT_COLOR}2. 恢复备份")
        print(f"{TEXT_COLOR}3. 删除备份")
        print(f"{TEXT_COLOR}4. 手动创建备份")
        print(f"{ERROR_COLOR}0. 返回主菜单")
        print(f"{SECONDARY_COLOR}{'=' * 40}")
        
        choice = input("请选择操作: ").strip()
        
        if choice == '1':
            list_backups()
        
        elif choice == '2':
            backups = list_backups()
            if backups:
                try:
                    idx = int(input(f"{TEXT_COLOR}请输入要恢复的备份编号: ").strip()) - 1
                    if 0 <= idx < len(backups):
                        restore_backup(backups[idx][1])
                    else:
                        print(f"{ERROR_COLOR}无效的编号")
                except ValueError:
                    print(f"{ERROR_COLOR}请输入有效的数字")
        
        elif choice == '3':
            backups = list_backups()
            if backups:
                try:
                    idx = int(input(f"{TEXT_COLOR}请输入要删除的备份编号: ").strip()) - 1
                    if 0 <= idx < len(backups):
                        delete_backup(backups[idx][1])
                    else:
                        print(f"{ERROR_COLOR}无效的编号")
                except ValueError:
                    print(f"{ERROR_COLOR}请输入有效的数字")
        
        elif choice == '4':
            backup_entries()
        
        elif choice == '0':
            break
        
        else:
            print(f"{ERROR_COLOR}无效选择，请重新输入")

def show_stats():
    """显示统计信息"""
    stats = get_diary_stats()
    
    print(f"\n{SECONDARY_COLOR}{'=' * 40}")
    print(f"{PRIMARY_COLOR}{Style.BRIGHT}        日记统计")
    print(f"{SECONDARY_COLOR}{'=' * 40}")
    print(f"{TEXT_COLOR}日记总数: {SECONDARY_COLOR}{stats['total_diaries']}")
    print(f"{TEXT_COLOR}总字数: {SECONDARY_COLOR}{stats['total_words']}")
    print(f"{TEXT_COLOR}总字符数: {SECONDARY_COLOR}{stats['total_chars']}")
    
    # 标签统计
    tag_stats = get_tag_stats()
    if tag_stats:
        print(f"\n{PRIMARY_COLOR}标签使用频率：")
        for i, tag_stat in enumerate(tag_stats[:10], 1):
            print(f"  {SECONDARY_COLOR}{i}.{TEXT_COLOR} {tag_stat['tag']} - {tag_stat['count']} 篇")

def date_input_with_relative(prompt="请输入日期 (YYYY-MM-DD)"):
    """支持相对日期的日期输入"""
    date_str = input(f"{TEXT_COLOR}{prompt} (或输入今天/昨天/3天前等): ").strip()
    
    # 尝试解析相对日期
    relative_date = parse_relative_date(date_str)
    if relative_date:
        return relative_date
    
    # 尝试解析标准日期格式
    try:
        datetime.strptime(date_str, DATE_FORMAT)
        return date_str
    except ValueError:
        return None

def export_diary_single():
    """导出单篇日记"""
    date_str = date_input_with_relative("请输入要导出的日记日期")
    if not date_str:
        print(f"{ERROR_COLOR}日期格式错误或日记不存在")
        return
    
    file_path = ENTRIES_DIR / f"{date_str}.txt"
    if not file_path.exists():
        print(f"{ERROR_COLOR}未找到 {date_str} 的日记")
        return
    
    export_path = export_diary(date_str)
    if export_path:
        print(f"{SUCCESS_COLOR}日记已导出至 {export_path}")

def export_all():
    """导出所有日记"""
    print(f"\n{TEXT_COLOR}正在导出所有日记...")
    exported, export_path = export_all_diaries()
    if exported:
        print(f"{SUCCESS_COLOR}已导出 {len(exported)} 篇日记至 {export_path}")
    else:
        print(f"{ACCENT_COLOR}暂无日记可导出")

def show_menu():
    """显示菜单"""
    print(f"\n{SECONDARY_COLOR}{'=' * 40}")
    print(f"{PRIMARY_COLOR}{Style.BRIGHT}        个人日记本")
    print(f"{SECONDARY_COLOR}{'=' * 40}")
    print(f"{TEXT_COLOR}1. 写日记（今天）")
    print(f"{TEXT_COLOR}2. 写日记（指定日期）")
    print(f"{TEXT_COLOR}3. 读日记")
    print(f"{TEXT_COLOR}4. 列出所有日记")
    print(f"{TEXT_COLOR}5. 搜索日记")
    print(f"{TEXT_COLOR}6. 删除日记")
    print(f"{TEXT_COLOR}7. 编辑日记")
    print(f"{TEXT_COLOR}8. 显示标签")
    print(f"{TEXT_COLOR}9. 备份管理")
    print(f"{TEXT_COLOR}A. 日记统计")
    print(f"{TEXT_COLOR}B. 导出日记")
    print(f"{TEXT_COLOR}C. 系统设置")
    print(f"{ERROR_COLOR}0. 退出")
    print(f"{SECONDARY_COLOR}{'=' * 40}")

def terminal_mode():
    """终端模式"""
    ensure_dir()
    
    while True:
        show_menu()
        choice = input("请选择操作: ").strip()
        
        if choice == '1':
            print(f"\n{PRIMARY_COLOR}【写日记 - 今天】")
            tags_str = input(f"{TEXT_COLOR}请输入标签（用逗号分隔多个标签，回车跳过）: ").strip()
            print(f"{TEXT_COLOR}（输入完成后，在新的一行输入 .end 并回车结束）")
            print(f"{TEXT_COLOR}（支持 Markdown 格式）")
            lines = []
            while True:
                line = input()
                if line == ".end":
                    break
                lines.append(line)
            content = "\n".join(lines)
            if content.strip():
                write_entry(content, tags_str=tags_str)
            else:
                print(f"{ERROR_COLOR}日记内容为空，未保存")
        
        elif choice == '2':
            date_str = input(f"{TEXT_COLOR}请输入日期 (格式 YYYY-MM-DD): ").strip()
            try:
                datetime.strptime(date_str, DATE_FORMAT)
            except ValueError:
                print(f"{ERROR_COLOR}日期格式错误，请使用 YYYY-MM-DD 格式")
                continue
            
            tags_str = input(f"{TEXT_COLOR}请输入标签（用逗号分隔多个标签，回车跳过）: ").strip()
            print(f"{TEXT_COLOR}请输入日记内容（输入 .end 结束）：")
            lines = []
            while True:
                line = input()
                if line == ".end":
                    break
                lines.append(line)
            content = "\n".join(lines)
            if content.strip():
                write_entry(content, date_str, tags_str=tags_str)
            else:
                print(f"{ERROR_COLOR}日记内容为空，未保存")

        elif choice == '3':
            date_str = input(f"{TEXT_COLOR}请输入要读取的日期 (YYYY-MM-DD): ").strip()
            read_entry(date_str)
        
        elif choice == '4':
            list_entries()

        elif choice == '5':
            keyword = input(f"{TEXT_COLOR}请输入搜索关键词: ").strip()
            if keyword:
                search_entries(keyword)
            else:
                print(f"{ERROR_COLOR}关键词不能为空")

        elif choice == '6':
            date_str = input(f"{TEXT_COLOR}请输入要删除的日期 (YYYY-MM-DD): ").strip()
            delete_entry(date_str)
        
        elif choice == '7':
            date_str = input(f"{TEXT_COLOR}请输入要编辑的日期 (YYYY-MM-DD): ").strip()
            edit_entry(date_str)
        
        elif choice == '8':
            show_tags()
        
        elif choice == '9':
            backup_management()
        
        elif choice.upper() == 'A':
            show_stats()
        
        elif choice.upper() == 'B':
            print(f"\n{SECONDARY_COLOR}{'=' * 40}")
            print(f"{PRIMARY_COLOR}{Style.BRIGHT}        导出日记")
            print(f"{SECONDARY_COLOR}{'=' * 40}")
            print(f"{TEXT_COLOR}1. 导出单篇日记")
            print(f"{TEXT_COLOR}2. 导出所有日记")
            print(f"{ERROR_COLOR}0. 返回")
            print(f"{SECONDARY_COLOR}{'=' * 40}")
            
            export_choice = input("请选择: ").strip()
            if export_choice == '1':
                export_diary_single()
            elif export_choice == '2':
                export_all()
        
        elif choice.upper() == 'C':
            show_settings()
        
        elif choice == '0':
            backup_entries()
            print(f"{SUCCESS_COLOR}再见！")
            break
        
        else:
            print(f"{ERROR_COLOR}无效选择，请重新输入")



def main():
    """主函数"""
    ensure_dir()

    print(f"\n{SECONDARY_COLOR}{'=' * 40}")
    print(f"{PRIMARY_COLOR}{Style.BRIGHT}        个人日记本")
    print(f"{SECONDARY_COLOR}{'=' * 40}")
    print(f"{TEXT_COLOR}1. 终端模式")
    print(f"{TEXT_COLOR}2. Web 应用模式")
    print(f"{ERROR_COLOR}0. 退出")
    print(f"{SECONDARY_COLOR}{'=' * 40}")

    choice = input("请选择运行模式: ").strip()

    if choice == '1':
        terminal_mode()
    elif choice == '2':
        print(f"{SUCCESS_COLOR}正在启动 Web 应用...")
        import os
        os.system('python app.py')
    elif choice == '0':
        print(f"{SUCCESS_COLOR}再见！")
    else:
        print(f"{ERROR_COLOR}无效选择，请重新运行程序")

if __name__ == "__main__":
    main()
