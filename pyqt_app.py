import sys
import os
import json
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QComboBox, QInputDialog, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt

# 配置
ENTRIES_DIR = Path("entries")
DATE_FORMAT = "%Y-%m-%d"
TAGS_FILE = Path("tags.json")

class DiaryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("个人日记本")
        self.setGeometry(100, 100, 800, 600)
        
        # 确保目录存在
        ENTRIES_DIR.mkdir(exist_ok=True)
        
        # 初始化标签文件
        self.init_tags_file()
        
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
    
    def init_tags_file(self):
        """初始化标签文件"""
        if not TAGS_FILE.exists():
            with open(TAGS_FILE, 'w', encoding='utf-8') as f:
                json.dump({}, f)
    
    def get_tags(self):
        """获取标签数据"""
        with open(TAGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_tags(self, tags):
        """保存标签数据"""
        with open(TAGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(tags, f, ensure_ascii=False, indent=2)
    
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
        file_path = ENTRIES_DIR / f"{date_str}.txt"
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
        
        file_path = ENTRIES_DIR / f"{date_str}.txt"
        
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
            self.update_tags_index(date_str, tags)
        
        QMessageBox.information(self, "成功", f"日记已保存至 {file_path}")
        self.refresh_entries()
    
    def update_tags_index(self, date_str, tags):
        """更新标签索引"""
        tag_data = self.get_tags()
        
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
        
        self.save_tags(tag_data)
    
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
            file_path = ENTRIES_DIR / f"{date_str}.txt"
            if file_path.exists():
                file_path.unlink()
                
                # 更新标签索引
                tag_data = self.get_tags()
                for tag, dates in tag_data.items():
                    if date_str in dates:
                        dates.remove(date_str)
                        if not dates:
                            del tag_data[tag]
                self.save_tags(tag_data)
                
                QMessageBox.information(self, "成功", f"已删除 {date_str} 的日记")
                self.refresh_entries()
                self.new_entry()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DiaryApp()
    window.show()
    sys.exit(app.exec())
