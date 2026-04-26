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

init(autoreset=True)



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
        confirm = input(f"{Fore.YELLOW}{date_str} 已有日记，是否覆盖？(y/n): ")
        if confirm.lower() != 'y':
            print(f"{Fore.RED}已取消写入")
            return

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    # 更新标签索引
    if tags_str:
        tags = [tag.strip() for tag in tags_str.split(',')]
        update_tags_index(date_str, tags)
    
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
        print(f"  {Fore.CYAN}{idx}.{Fore.WHITE} {date_str} {Style.DIM}({size} 字节){Style.RESET_ALL}")

def search_entries(keyword):
    """在日记内容中搜索关键词"""
    results = search_entries_util(keyword)
    if results:
        print(f"\n{Fore.GREEN}找到包含 '{keyword}' 的日记：")
        for date_str, matches in results:
            print(f"\n  {Fore.CYAN}•{Fore.WHITE} {date_str}")
            for line_num, context in matches:
                print(f"    {Fore.YELLOW}第 {line_num} 行:")
                for i, line in enumerate(context):
                    if i == 1:  # 匹配的行
                        print(f"      {Fore.GREEN}{line.strip()}")
                    else:  # 上下文行
                        print(f"      {Fore.WHITE}{line.strip()}")
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
        
        # 更新标签索引
        tag_data = get_tags()
        for tag, dates in tag_data.items():
            if date_str in dates:
                dates.remove(date_str)
                if not dates:
                    del tag_data[tag]
        save_tags(tag_data)
        
        print(f"{Fore.GREEN}已删除 {date_str} 的日记")
    else:
        print(f"{Fore.YELLOW}已取消删除")

def edit_entry(date_str):
    """编辑已存在的日记"""
    file_path = get_file_path(date_str)

    if not file_path.exists():
        print(f"{Fore.RED}未找到 {date_str} 的日记")
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
    print(f"\n{Fore.CYAN}【编辑日记 - {date_str}】")
    print(f"{Fore.WHITE}现有标签: {tags_str or '无'}")
    print(f"{Fore.WHITE}现有内容:")
    print(f"{Fore.WHITE}{existing_content}")
    print(f"{Fore.WHITE}（输入新内容，结束后输入 .end 并回车）")

    # 输入新标签
    new_tags_str = input(f"{Fore.WHITE}请输入新标签（用逗号分隔多个标签，回车保持原有标签）: ").strip()
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

        print(f"{Fore.GREEN}日记已更新")
    else:
        print(f"{Fore.RED}内容为空，未更新")

def show_tags():
    """显示所有标签"""
    tag_data = get_tags()
    if not tag_data:
        print(f"{Fore.YELLOW}暂无标签")
        return
    
    print(f"\n{Fore.GREEN}所有标签：")
    for tag, dates in tag_data.items():
        print(f"  {Fore.CYAN}{tag}{Fore.WHITE} ({len(dates)} 篇日记)")

def backup_entries():
    """备份 entries 文件夹"""
    backup_dir = backup_entries_util()
    if backup_dir:
        print(f"{Fore.GREEN}日记已备份至 {backup_dir}")

def list_backups():
    """列出所有备份"""
    backups = list_backups_util()
    if not backups:
        print(f"{Fore.YELLOW}暂无备份")
        return
    
    print(f"\n{Fore.GREEN}所有备份：")
    for idx, (timestamp, backup_dir) in enumerate(backups, 1):
        # 计算备份大小
        size = sum(f.stat().st_size for f in backup_dir.rglob("*"))
        print(f"  {Fore.CYAN}{idx}.{Fore.WHITE} {timestamp.strftime('%Y-%m-%d %H:%M:%S')} ({size} 字节) - {backup_dir.name}")
    
    return backups

def restore_backup(backup_dir):
    """恢复备份"""
    if not backup_dir.exists():
        print(f"{Fore.RED}备份目录不存在")
        return
    
    # 确认恢复
    confirm = input(f"{Fore.RED}确认恢复备份 {backup_dir.name} 吗？这将覆盖当前的日记！(y/n): ")
    if confirm.lower() != 'y':
        print(f"{Fore.YELLOW}已取消恢复")
        return
    
    success = restore_backup_util(backup_dir)
    if success:
        print(f"{Fore.GREEN}备份已恢复")

def delete_backup(backup_dir):
    """删除备份"""
    if not backup_dir.exists():
        print(f"{Fore.RED}备份目录不存在")
        return
    
    confirm = input(f"{Fore.RED}确认删除备份 {backup_dir.name} 吗？(y/n): ")
    if confirm.lower() == 'y':
        success = delete_backup_util(backup_dir)
        if success:
            print(f"{Fore.GREEN}备份已删除")
    else:
        print(f"{Fore.YELLOW}已取消删除")

def backup_management():
    """备份管理"""
    while True:
        print(f"\n{Fore.CYAN}{'=' * 40}")
        print(f"{Fore.GREEN}{Style.BRIGHT}        备份管理")
        print(f"{Fore.CYAN}{'=' * 40}")
        print(f"{Fore.WHITE}1. 列出所有备份")
        print(f"{Fore.WHITE}2. 恢复备份")
        print(f"{Fore.WHITE}3. 删除备份")
        print(f"{Fore.WHITE}4. 手动创建备份")
        print(f"{Fore.RED}0. 返回主菜单")
        print(f"{Fore.CYAN}{'=' * 40}")
        
        choice = input("请选择操作: ").strip()
        
        if choice == '1':
            list_backups()
        
        elif choice == '2':
            backups = list_backups()
            if backups:
                try:
                    idx = int(input(f"{Fore.WHITE}请输入要恢复的备份编号: ").strip()) - 1
                    if 0 <= idx < len(backups):
                        restore_backup(backups[idx][1])
                    else:
                        print(f"{Fore.RED}无效的编号")
                except ValueError:
                    print(f"{Fore.RED}请输入有效的数字")
        
        elif choice == '3':
            backups = list_backups()
            if backups:
                try:
                    idx = int(input(f"{Fore.WHITE}请输入要删除的备份编号: ").strip()) - 1
                    if 0 <= idx < len(backups):
                        delete_backup(backups[idx][1])
                    else:
                        print(f"{Fore.RED}无效的编号")
                except ValueError:
                    print(f"{Fore.RED}请输入有效的数字")
        
        elif choice == '4':
            backup_entries()
        
        elif choice == '0':
            break
        
        else:
            print(f"{Fore.RED}无效选择，请重新输入")

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
    print(f"{Fore.WHITE}7. 编辑日记")
    print(f"{Fore.WHITE}8. 显示标签")
    print(f"{Fore.WHITE}9. 备份管理")
    print(f"{Fore.RED}0. 退出")
    print(f"{Fore.CYAN}{'=' * 40}")

def terminal_mode():
    """终端模式"""
    ensure_dir()
    
    while True:
        show_menu()
        choice = input("请选择操作: ").strip()
        
        if choice == '1':
            print(f"\n{Fore.GREEN}【写日记 - 今天】")
            tags_str = input(f"{Fore.WHITE}请输入标签（用逗号分隔多个标签，回车跳过）: ").strip()
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
                write_entry(content, tags_str=tags_str)
            else:
                print(f"{Fore.RED}日记内容为空，未保存")
        
        elif choice == '2':
            date_str = input(f"{Fore.WHITE}请输入日期 (格式 YYYY-MM-DD): ").strip()
            try:
                datetime.strptime(date_str, DATE_FORMAT)
            except ValueError:
                print(f"{Fore.RED}日期格式错误，请使用 YYYY-MM-DD 格式")
                continue
            
            tags_str = input(f"{Fore.WHITE}请输入标签（用逗号分隔多个标签，回车跳过）: ").strip()
            print(f"{Fore.WHITE}请输入日记内容（输入 .end 结束）：")
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
        
        elif choice == '7':
            date_str = input(f"{Fore.WHITE}请输入要编辑的日期 (YYYY-MM-DD): ").strip()
            edit_entry(date_str)
        
        elif choice == '8':
            show_tags()
        
        elif choice == '9':
            backup_management()

        elif choice == '0':
            backup_entries()
            print(f"{Fore.GREEN}再见！")
            break
        
        else:
            print(f"{Fore.RED}无效选择，请重新输入")

def pyqt_mode():
    """PyQt 图形化模式"""
    try:
        from PyQt6.QtWidgets import (
            QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
            QPushButton, QTextEdit, QLabel, QLineEdit, QListWidget, QListWidgetItem,
            QComboBox, QInputDialog, QMessageBox, QSplitter
        )
        from PyQt6.QtCore import Qt
    except ImportError:
        print(f"{Fore.RED}PyQt6 未安装，请运行 'pip install PyQt6' 后重试")
        return
    
    class DiaryApp(QMainWindow):
        def __init__(self):
            super().__init__()
            self.setWindowTitle("个人日记本")
            self.setGeometry(100, 100, 800, 600)
            
            # 确保目录存在
            ensure_dir()
            
            # 创建主布局
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            
            main_layout = QVBoxLayout(central_widget)
            
            # 创建顶部工具栏
            toolbar = QHBoxLayout()
            
            self.btn_new = QPushButton("新建日记")
            self.btn_new.clicked.connect(self.new_entry)
            toolbar.addWidget(self.btn_new)
            
            self.btn_read = QPushButton("读取日记")
            self.btn_read.clicked.connect(self.read_entry)
            toolbar.addWidget(self.btn_read)
            
            self.btn_delete = QPushButton("删除日记")
            self.btn_delete.clicked.connect(self.delete_entry)
            toolbar.addWidget(self.btn_delete)
            
            self.btn_refresh = QPushButton("刷新列表")
            self.btn_refresh.clicked.connect(self.refresh_entries)
            toolbar.addWidget(self.btn_refresh)
            
            main_layout.addLayout(toolbar)
            
            # 创建分割器
            splitter = QSplitter(Qt.Orientation.Horizontal)
            
            # 左侧日记列表
            self.entries_list = QListWidget()
            self.entries_list.itemClicked.connect(self.on_entry_clicked)
            splitter.addWidget(self.entries_list)
            
            # 右侧内容区域
            content_widget = QWidget()
            content_layout = QVBoxLayout(content_widget)
            
            # 日期选择
            date_layout = QHBoxLayout()
            date_layout.addWidget(QLabel("日期:"))
            self.date_edit = QLineEdit()
            self.date_edit.setText(datetime.now().strftime(DATE_FORMAT))
            date_layout.addWidget(self.date_edit)
            content_layout.addLayout(date_layout)
            
            # 标签输入
            tags_layout = QHBoxLayout()
            tags_layout.addWidget(QLabel("标签:"))
            self.tags_edit = QLineEdit()
            self.tags_edit.setPlaceholderText("用逗号分隔多个标签")
            tags_layout.addWidget(self.tags_edit)
            content_layout.addLayout(tags_layout)
            
            # 内容编辑
            content_layout.addWidget(QLabel("内容:"))
            self.content_edit = QTextEdit()
            content_layout.addWidget(self.content_edit)
            
            # 保存按钮
            self.btn_save = QPushButton("保存")
            self.btn_save.clicked.connect(self.save_entry)
            content_layout.addWidget(self.btn_save)
            
            splitter.addWidget(content_widget)
            splitter.setSizes([200, 600])
            main_layout.addWidget(splitter)
            
            # 刷新日记列表
            self.refresh_entries()
        
        def refresh_entries(self):
            """刷新日记列表"""
            self.entries_list.clear()
            entries = sorted(ENTRIES_DIR.glob("*.txt"), reverse=True)
            for entry in entries:
                date_str = entry.stem
                size = entry.stat().st_size
                item = QListWidgetItem(f"{date_str} ({size} 字节)")
                item.setData(Qt.ItemDataRole.UserRole, date_str)
                self.entries_list.addItem(item)
        
        def new_entry(self):
            """新建日记"""
            self.date_edit.setText(datetime.now().strftime(DATE_FORMAT))
            self.tags_edit.clear()
            self.content_edit.clear()
        
        def on_entry_clicked(self, item):
            """点击日记项"""
            date_str = item.data(Qt.ItemDataRole.UserRole)
            self.load_entry(date_str)
        
        def load_entry(self, date_str):
            """加载日记内容"""
            file_path = get_file_path(date_str)
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 提取标签（如果有）
                lines = content.split('\n')
                tags_line = ""
                if lines and lines[0].startswith("Tags: "):
                    tags_line = lines[0][6:]
                    content = '\n'.join(lines[1:])
                
                self.date_edit.setText(date_str)
                self.tags_edit.setText(tags_line)
                self.content_edit.setPlainText(content)
        
        def save_entry(self):
            """保存日记"""
            date_str = self.date_edit.text().strip()
            tags_str = self.tags_edit.text().strip()
            content = self.content_edit.toPlainText().strip()
            
            if not date_str:
                QMessageBox.warning(self, "警告", "请输入日期")
                return
            
            if not content:
                QMessageBox.warning(self, "警告", "日记内容不能为空")
                return
            
            # 验证日期格式
            try:
                datetime.strptime(date_str, DATE_FORMAT)
            except ValueError:
                QMessageBox.warning(self, "警告", "日期格式错误，请使用 YYYY-MM-DD 格式")
                return
            
            file_path = get_file_path(date_str)
            
            # 构建内容（包含标签）
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            full_content = f"[{timestamp}]\n"
            if tags_str:
                full_content += f"Tags: {tags_str}\n"
            full_content += content
            
            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            # 更新标签索引
            if tags_str:
                tags = [tag.strip() for tag in tags_str.split(',')]
                update_tags_index(date_str, tags)
            
            QMessageBox.information(self, "成功", f"日记已保存至 {file_path}")
            self.refresh_entries()
        
        def read_entry(self):
            """读取指定日期的日记"""
            date_str, ok = QInputDialog.getText(self, "读取日记", "请输入日期 (YYYY-MM-DD):")
            if ok and date_str:
                self.load_entry(date_str)
        
        def delete_entry(self):
            """删除日记"""
            selected_items = self.entries_list.selectedItems()
            if not selected_items:
                QMessageBox.warning(self, "警告", "请选择要删除的日记")
                return
            
            item = selected_items[0]
            date_str = item.data(Qt.ItemDataRole.UserRole)
            
            reply = QMessageBox.question(
                self, "确认删除", f"确定要删除 {date_str} 的日记吗？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                file_path = get_file_path(date_str)
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
                    
                    QMessageBox.information(self, "成功", f"已删除 {date_str} 的日记")
                    self.refresh_entries()
                    self.new_entry()
    
    app = QApplication(sys.argv)
    window = DiaryApp()
    window.show()
    sys.exit(app.exec())

def main():
    """主函数"""
    ensure_dir()
    
    print(f"\n{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.GREEN}{Style.BRIGHT}        个人日记本")
    print(f"{Fore.CYAN}{'=' * 40}")
    print(f"{Fore.WHITE}1. 终端模式")
    print(f"{Fore.WHITE}2. PyQt 图形化模式")
    print(f"{Fore.RED}0. 退出")
    print(f"{Fore.CYAN}{'=' * 40}")
    
    choice = input("请选择运行模式: ").strip()
    
    if choice == '1':
        terminal_mode()
    elif choice == '2':
        pyqt_mode()
    elif choice == '0':
        print(f"{Fore.GREEN}再见！")
    else:
        print(f"{Fore.RED}无效选择，请重新运行程序")

if __name__ == "__main__":
    main()
