#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt 图形化界面模块
"""

import sys
import os
from pathlib import Path
from datetime import datetime
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QTextEdit, QPushButton, QListWidget, QListWidgetItem, QLabel, 
    QInputDialog, QMessageBox, QSplitter, QMenu, QMenuBar, QAction,
    QLineEdit, QComboBox, QDateEdit, QFormLayout, QDialog
)
from PyQt6.QtCore import Qt, QSize, QDate, QTimer
from PyQt6.QtGui import QFont, QIcon

from utils.storage import (
    ensure_dir, get_today_str, get_file_path, get_tags, save_tags, 
    update_tags_index, get_entry_content, get_entries, clear_entry_cache
)
from utils.backup import backup_entries, list_backups, restore_backup, delete_backup
from utils.search import search_entries_util
from utils.config import ENTRIES_DIR, TAGS_FILE, BACKUPS_DIR, get_config
from utils.stats import get_stats
from utils.logger import logger

class DiaryApp(QMainWindow):
    """日记本应用主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("日记本")
        self.setGeometry(100, 100, 1000, 700)
        self.current_date = get_today_str()
        self.last_save_time = datetime.now()
        self.init_ui()
        self.init_auto_save()
    
    def init_ui(self):
        """初始化界面"""
        # 菜单栏
        self.init_menu()
        
        # 主布局
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget)
        
        # 左侧日记列表
        self.entries_list = QListWidget()
        self.entries_list.setMinimumWidth(250)
        self.entries_list.itemClicked.connect(self.on_entry_clicked)
        
        # 右侧编辑区
        right_layout = QVBoxLayout()
        
        # 日期选择
        date_layout = QHBoxLayout()
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.on_date_changed)
        
        # 标签输入
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入标签，用逗号分隔")
        
        date_layout.addWidget(QLabel("日期："))
        date_layout.addWidget(self.date_edit)
        date_layout.addWidget(QLabel("标签："))
        date_layout.addWidget(self.tag_input)
        
        # 文本编辑区
        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("SimHei", 11))
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.save_button.clicked.connect(self.save_entry)
        
        self.new_button = QPushButton("新建")
        self.new_button.clicked.connect(self.new_entry)
        
        self.delete_button = QPushButton("删除")
        self.delete_button.clicked.connect(self.delete_entry)
        
        self.backup_button = QPushButton("备份")
        self.backup_button.clicked.connect(self.show_backup_menu)
        
        toolbar.addWidget(self.new_button)
        toolbar.addWidget(self.save_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addWidget(self.backup_button)
        
        right_layout.addLayout(date_layout)
        right_layout.addWidget(self.text_edit)
        right_layout.addLayout(toolbar)
        
        # 分割器
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.entries_list)
        
        right_widget = QWidget()
        right_widget.setLayout(right_layout)
        splitter.addWidget(right_widget)
        
        splitter.setSizes([250, 750])
        main_layout.addWidget(splitter)
        
        self.setCentralWidget(central_widget)
        self.load_entries()
        self.load_entry_content()
    
    def init_auto_save(self):
        """初始化自动保存功能"""
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(self.auto_save)
        
        # 启动自动保存
        self.start_auto_save()
    
    def start_auto_save(self):
        """启动自动保存"""
        config = get_config()
        if config.get('auto_save', True):
            interval = config.get('auto_save_interval', 30) * 1000  # 转换为毫秒
            self.auto_save_timer.start(interval)
        else:
            self.auto_save_timer.stop()
    
    def auto_save(self):
        """自动保存功能"""
        content = self.text_edit.toPlainText().strip()
        if content:
            # 检查是否有内容变化
            current_time = datetime.now()
            time_diff = (current_time - self.last_save_time).total_seconds()
            
            # 只有当内容有变化且时间间隔超过1秒时才保存
            if time_diff > 1:
                try:
                    # 调用保存方法
                    self.save_entry(auto=True)
                except Exception as e:
                    logger.error(f"自动保存失败: {str(e)}")
    
    def init_menu(self):
        """初始化菜单栏"""
        menubar = self.menuBar()
        
        # 文件菜单
        file_menu = menubar.addMenu("文件")
        
        new_action = QAction("新建", self)
        new_action.triggered.connect(self.new_entry)
        file_menu.addAction(new_action)
        
        save_action = QAction("保存", self)
        save_action.triggered.connect(self.save_entry)
        file_menu.addAction(save_action)
        
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_entry)
        file_menu.addAction(delete_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # 工具菜单
        tool_menu = menubar.addMenu("工具")
        
        backup_action = QAction("备份管理", self)
        backup_action.triggered.connect(self.show_backup_menu)
        tool_menu.addAction(backup_action)
        
        search_action = QAction("搜索", self)
        search_action.triggered.connect(self.show_search_dialog)
        tool_menu.addAction(search_action)
        
        stats_action = QAction("统计", self)
        stats_action.triggered.connect(self.show_stats)
        tool_menu.addAction(stats_action)
    
    def load_entries(self):
        """加载日记列表"""
        self.entries_list.clear()
        entries = get_entries()
        for entry in entries:
            date_str = entry.stem
            item = QListWidgetItem(date_str)
            self.entries_list.addItem(item)
    
    def load_entry_content(self):
        """加载当前日期的日记内容"""
        try:
            timestamp, tags, content = get_entry_content(self.current_date)
            self.text_edit.setPlainText(content)
            self.tag_input.setText(", ".join(tags))
        except:
            self.text_edit.clear()
            self.tag_input.clear()
    
    def on_entry_clicked(self, item):
        """点击日记项时的处理"""
        self.current_date = item.text()
        # 更新日期选择器
        year = int(self.current_date[:4])
        month = int(self.current_date[5:7])
        day = int(self.current_date[8:10])
        self.date_edit.setDate(QDate(year, month, day))
        self.load_entry_content()
    
    def on_date_changed(self, date):
        """日期变更时的处理"""
        year = date.year()
        month = date.month()
        day = date.day()
        self.current_date = f"{year:04d}-{month:02d}-{day:02d}"
        self.load_entry_content()
    
    def save_entry(self, auto=False):
        """保存日记"""
        content = self.text_edit.toPlainText()
        if not content.strip():
            if not auto:
                QMessageBox.warning(self, "警告", "日记内容不能为空")
            return
        
        tags_str = self.tag_input.text().strip()
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
        
        try:
            file_path = get_file_path(self.current_date)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(f"# {self.current_date}\n\n")
                f.write(f"**时间：** {datetime.now().strftime('%H:%M:%S')}\n\n")
                if tags:
                    f.write(f"**标签：** {', '.join(tags)}\n\n")
                f.write(content)
            
            # 更新标签索引
            update_tags_index(self.current_date, tags)
            
            # 清除缓存
            clear_entry_cache(self.current_date)
            
            # 刷新列表（只在手动保存时）
            if not auto:
                self.load_entries()
                
                # 选中当前日期
                for i in range(self.entries_list.count()):
                    item = self.entries_list.item(i)
                    if item.text() == self.current_date:
                        self.entries_list.setCurrentItem(item)
                        break
                
                QMessageBox.information(self, "成功", "日记保存成功")
            
            # 更新最后保存时间
            self.last_save_time = datetime.now()
            
            logger.info(f"{'自动' if auto else ''}保存日记: {self.current_date}")
        except Exception as e:
            if not auto:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")
            logger.error(f"保存日记失败: {str(e)}")
    
    def new_entry(self):
        """新建日记"""
        self.current_date = get_today_str()
        self.date_edit.setDate(QDate.currentDate())
        self.text_edit.clear()
        self.tag_input.clear()
    
    def delete_entry(self):
        """删除日记"""
        if not self.current_date:
            QMessageBox.warning(self, "警告", "请先选择要删除的日记")
            return
        
        reply = QMessageBox.question(
            self, "确认", f"确定要删除 {self.current_date} 的日记吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                file_path = get_file_path(self.current_date)
                if file_path.exists():
                    file_path.unlink()
                
                # 更新标签索引
                update_tags_index(self.current_date, [])
                
                # 刷新列表
                self.load_entries()
                self.text_edit.clear()
                self.tag_input.clear()
                
                QMessageBox.information(self, "成功", "日记删除成功")
                logger.info(f"删除日记: {self.current_date}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
                logger.error(f"删除日记失败: {str(e)}")
    
    def show_backup_menu(self):
        """显示备份菜单"""
        backup_dialog = QDialog(self)
        backup_dialog.setWindowTitle("备份管理")
        backup_dialog.setGeometry(200, 200, 600, 400)
        
        layout = QVBoxLayout(backup_dialog)
        
        # 备份列表
        backup_list = QListWidget()
        backups = list_backups()
        for backup in backups:
            item = QListWidgetItem(f"{backup['name']} ({backup['size']} MB)")
            backup_list.addItem(item)
        
        # 按钮
        button_layout = QHBoxLayout()
        
        create_button = QPushButton("创建备份")
        create_button.clicked.connect(lambda: self.create_backup(backup_dialog, backup_list))
        
        restore_button = QPushButton("恢复备份")
        restore_button.clicked.connect(lambda: self.restore_selected_backup(backup_dialog, backup_list))
        
        delete_button = QPushButton("删除备份")
        delete_button.clicked.connect(lambda: self.delete_selected_backup(backup_dialog, backup_list))
        
        button_layout.addWidget(create_button)
        button_layout.addWidget(restore_button)
        button_layout.addWidget(delete_button)
        
        layout.addWidget(backup_list)
        layout.addLayout(button_layout)
        
        backup_dialog.exec()
    
    def create_backup(self, dialog, backup_list):
        """创建备份"""
        try:
            backup_name = backup_entries()
            QMessageBox.information(self, "成功", f"备份创建成功: {backup_name}")
            
            # 刷新备份列表
            backup_list.clear()
            backups = list_backups()
            for backup in backups:
                item = QListWidgetItem(f"{backup['name']} ({backup['size']} MB)")
                backup_list.addItem(item)
            
            logger.info(f"创建备份: {backup_name}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"备份失败: {str(e)}")
            logger.error(f"创建备份失败: {str(e)}")
    
    def restore_selected_backup(self, dialog, backup_list):
        """恢复选中的备份"""
        selected_item = backup_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要恢复的备份")
            return
        
        backup_name = selected_item.text().split(' ')[0]
        
        reply = QMessageBox.question(
            self, "确认", f"确定要恢复备份 {backup_name} 吗？这将覆盖当前的日记数据。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                restore_backup(backup_name)
                QMessageBox.information(self, "成功", "备份恢复成功")
                
                # 刷新日记列表
                self.load_entries()
                self.load_entry_content()
                
                logger.info(f"恢复备份: {backup_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"恢复失败: {str(e)}")
                logger.error(f"恢复备份失败: {str(e)}")
    
    def delete_selected_backup(self, dialog, backup_list):
        """删除选中的备份"""
        selected_item = backup_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "警告", "请选择要删除的备份")
            return
        
        backup_name = selected_item.text().split(' ')[0]
        
        reply = QMessageBox.question(
            self, "确认", f"确定要删除备份 {backup_name} 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                delete_backup(backup_name)
                
                # 刷新备份列表
                backup_list.clear()
                backups = list_backups()
                for backup in backups:
                    item = QListWidgetItem(f"{backup['name']} ({backup['size']} MB)")
                    backup_list.addItem(item)
                
                QMessageBox.information(self, "成功", "备份删除成功")
                logger.info(f"删除备份: {backup_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
                logger.error(f"删除备份失败: {str(e)}")
    
    def show_search_dialog(self):
        """显示搜索对话框"""
        keyword, ok = QInputDialog.getText(self, "搜索", "请输入搜索关键词:")
        if ok and keyword:
            try:
                results = search_entries_util(keyword)
                
                if not results:
                    QMessageBox.information(self, "结果", "未找到相关日记")
                    return
                
                # 显示搜索结果
                result_dialog = QDialog(self)
                result_dialog.setWindowTitle("搜索结果")
                result_dialog.setGeometry(200, 200, 800, 600)
                
                layout = QVBoxLayout(result_dialog)
                
                result_list = QListWidget()
                for date_str, matches in results:
                    item = QListWidgetItem(f"{date_str} - {len(matches)} 个匹配")
                    item.setData(Qt.ItemDataRole.UserRole, (date_str, matches))
                    result_list.addItem(item)
                
                result_list.itemDoubleClicked.connect(lambda item: self.show_search_result(item, result_dialog))
                
                layout.addWidget(result_list)
                result_dialog.exec()
                
                logger.info(f"搜索关键词: {keyword}, 找到 {len(results)} 个结果")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"搜索失败: {str(e)}")
                logger.error(f"搜索失败: {str(e)}")
    
    def show_search_result(self, item, dialog):
        """显示搜索结果详情"""
        date_str, matches = item.data(Qt.ItemDataRole.UserRole)
        
        # 切换到该日记
        self.current_date = date_str
        year = int(date_str[:4])
        month = int(date_str[5:7])
        day = int(date_str[8:10])
        self.date_edit.setDate(QDate(year, month, day))
        self.load_entry_content()
        
        # 关闭搜索结果对话框
        dialog.accept()
    
    def show_stats(self):
        """显示统计信息"""
        try:
            stats = get_stats()
            
            stats_text = f"""
日记总数: {stats['total_entries']}
总字数: {stats['total_words']}
总字符数: {stats['total_chars']}
总标签数: {stats['total_tags']}
            """
            
            QMessageBox.information(self, "统计信息", stats_text)
            logger.info("查看统计信息")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"获取统计信息失败: {str(e)}")
            logger.error(f"获取统计信息失败: {str(e)}")

def pyqt_mode():
    """运行 PyQt 图形化模式"""
    app = QApplication(sys.argv)
    window = DiaryApp()
    window.show()
    sys.exit(app.exec())
