import os
import shutil
from datetime import datetime
from pathlib import Path
import markdown
from colorama import init, Fore, Style

init(autoreset=True)

# 配置
ENTRIES_DIR = Path("entries")
DATE_FORMAT = "%Y-%m-%d"

def ensure_dir():
    """确保日记存放目录存在"""
    ENTRIES_DIR.mkdir(exist_ok=True)

def get_today_str():
    """获取今天的日期字符串"""
    return datetime.now().strftime(DATE_FORMAT)

def get_file_path(date_str):
    """根据日期字符串获取文件路径"""
    return ENTRIES_DIR / f"{date_str}.txt"

def write_entry(content, date_str=None):
    """写日记（默认今天）"""
    if date_str is None:
        date_str = get_today_str()

    file_path = get_file_path(date_str)

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    content = f"[{timestamp}]\n{content}"

    if file_path.exists():
        confirm = input(f"{Fore.YELLOW}{date_str} 已有日记，是否覆盖？(y/n): ")
        if confirm.lower() != 'y':
            print(f"{Fore.RED}已取消写入")
            return

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"{Fore.GREEN}日记已保存至 {file_path}")

def read_entry(date_str):
    """读取指定日期的日记"""
    file_path = get_file_path(date_str)

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        print(f"\n{Fore.CYAN}{'=' * 40}")
        print(f"{Fore.CYAN}        {date_str} 的日记")
        print(f"{Fore.CYAN}{'=' * 40}")

        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                print(f"{Fore.GREEN}{Style.BRIGHT}{line[2:]}")
            elif line.startswith('## '):
                print(f"{Fore.GREEN}{line[3:]}")
            elif line.startswith('### '):
                print(f"{Fore.CYAN}{line[4:]}")
            elif line.startswith('**') and line.endswith('**'):
                print(f"{Fore.YELLOW}{Style.BRIGHT}{line[2:-2]}")
            elif line.startswith('*') and line.endswith('*'):
                print(f"{Fore.MAGENTA}{line[1:-1]}")
            elif line.startswith('- ') or line.startswith('* '):
                print(f"{Fore.WHITE}  {Fore.YELLOW}•{Fore.WHITE} {line[2:]}")
            elif line.startswith('> '):
                print(f"{Fore.BLUE}  │ {line[2:]}")
            elif line.strip():
                print(f"{Fore.WHITE}{line}")
            else:
                print()
    except FileNotFoundError:
        print(f"{Fore.RED}未找到 {date_str} 的日记")

def list_entries():
    """列出所有日记的日期"""
    entries = sorted(ENTRIES_DIR.glob("*.txt"))
    if not entries:
        print(f"{Fore.YELLOW}暂无日记")
        return

    print(f"\n{Fore.GREEN}已有日记：")
    for idx, entry in enumerate(entries, 1):
        date_str = entry.stem
        size = entry.stat().st_size
        print(f"  {Fore.CYAN}{idx}.{Fore.WHITE} {date_str} {Fore.DIM}({size} 字节)")

def search_entries(keyword):
    """在日记内容中搜索关键词"""
    entries = ENTRIES_DIR.glob("*.txt")
    results = []
    
    for entry in entries:
        with open(entry, 'r', encoding='utf-8') as f:
            content = f.read()
            if keyword in content:
                results.append(entry.stem)
    
    if results:
        print(f"\n{Fore.GREEN}找到包含 '{keyword}' 的日记：")
        for date_str in results:
            print(f"  {Fore.CYAN}•{Fore.WHITE} {date_str}")
    else:
        print(f"{Fore.YELLOW}未找到包含 '{keyword}' 的日记")

def delete_entry(date_str):
    """删除指定日期的日记"""
    file_path = get_file_path(date_str)

    if not file_path.exists():
        print(f"{Fore.RED}未找到 {date_str} 的日记")
        return

    confirm = input(f"{Fore.RED}确认删除 {date_str} 的日记？(y/n): ")
    if confirm.lower() == 'y':
        file_path.unlink()
        print(f"{Fore.GREEN}已删除 {date_str} 的日记")
    else:
        print(f"{Fore.YELLOW}已取消删除")

def show_menu():
    """显示菜单"""
    print(f"\n{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.GREEN}{Style.BRIGHT}        个人日记本")
    print(f"{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.WHITE}1. 写日记（今天）")
    print(f"{Fore.WHITE}2. 写日记（指定日期）")
    print(f"{Fore.WHITE}3. 读日记")
    print(f"{Fore.WHITE}4. 列出所有日记")
    print(f"{Fore.WHITE}5. 搜索日记")
    print(f"{Fore.WHITE}6. 删除日记")
    print(f"{Fore.RED}0. 退出")
    print(f"{Fore.CYAN}{'=' * 40}")

def backup_entries():
    """备份 entries 文件夹"""
    if not ENTRIES_DIR.exists() or not any(ENTRIES_DIR.iterdir()):
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path(f"entries_backup_{timestamp}")
    shutil.copytree(ENTRIES_DIR, backup_dir)
    print(f"{Fore.GREEN}日记已备份至 {backup_dir}")

def main():
    ensure_dir()
    
    while True:
        show_menu()
        choice = input("请选择操作: ").strip()
        
        if choice == '1':
            print(f"\n{Fore.GREEN}【写日记 - 今天】")
            print(f"{Fore.WHITE}（输入完成后，在新的一行输入 .end 并回车结束）")
            print(f"{Fore.WHITE}（支持 Markdown 格式）")
            lines = []
            while True:
                line = input()
                if line == ".end":
                    break
                lines.append(line)
            content = "\n".join(lines)
            if content.strip():
                write_entry(content)
            else:
                print(f"{Fore.RED}日记内容为空，未保存")
        
        elif choice == '2':
            date_str = input(f"{Fore.WHITE}请输入日期 (格式 YYYY-MM-DD): ").strip()
            try:
                datetime.strptime(date_str, DATE_FORMAT)
            except ValueError:
                print(f"{Fore.RED}日期格式错误，请使用 YYYY-MM-DD 格式")
                continue
            
            print(f"{Fore.WHITE}请输入日记内容（输入 .end 结束）：")
            lines = []
            while True:
                line = input()
                if line == ".end":
                    break
                lines.append(line)
            content = "\n".join(lines)
            if content.strip():
                write_entry(content, date_str)
            else:
                print(f"{Fore.RED}日记内容为空，未保存")

        elif choice == '3':
            date_str = input(f"{Fore.WHITE}请输入要读取的日期 (YYYY-MM-DD): ").strip()
            read_entry(date_str)
        
        elif choice == '4':
            list_entries()

        elif choice == '5':
            keyword = input(f"{Fore.WHITE}请输入搜索关键词: ").strip()
            if keyword:
                search_entries(keyword)
            else:
                print(f"{Fore.RED}关键词不能为空")

        elif choice == '6':
            date_str = input(f"{Fore.WHITE}请输入要删除的日期 (YYYY-MM-DD): ").strip()
            delete_entry(date_str)

        elif choice == '0':
            backup_entries()
            print(f"{Fore.GREEN}再见！")
            break

        else:
            print(f"{Fore.RED}无效选择，请重新输入")

if __name__ == "__main__":
    main()