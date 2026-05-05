#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PyQt 图形化界面模块 - 增强版
功能对齐 Web 版本
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QPushButton, QListWidget, QListWidgetItem, QLabel,
    QInputDialog, QMessageBox, QSplitter, QMenu, QMenuBar,
    QLineEdit, QComboBox, QDateEdit, QFormLayout, QDialog, QTabWidget,
    QCheckBox, QGroupBox, QProgressBar, QTableWidget, QTableWidgetItem,
    QHeaderView, QScrollArea, QFrame, QToolButton, QStatusBar,
    QDialogButtonBox, QGridLayout
)
from PyQt6.QtCore import Qt, QSize, QDate, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QIcon, QAction, QColor, QPalette, QBrush

from utils.storage import (
    ensure_dir, get_today_str, get_file_path, get_tags, save_tags,
    update_tags_index, get_entry_content, get_entries, clear_entry_cache,
    save_entry, delete_entry as storage_delete_entry
)
from utils.backup import backup_entries, list_backups, restore_backup, delete_backup
from utils.search import search_entries
from utils.config import ENTRIES_DIR, TAGS_FILE, get_config, save_config
from utils.stats import get_diary_stats, get_tag_stats
from utils.mood import get_mood, save_mood, MOOD_TYPES
from utils.streak import get_user_streak_info, get_streak_message, get_streak_reward, update_streak_on_entry
from utils.challenges import get_active_challenge, start_challenge, get_all_challenges_status
from utils.habits import get_writing_heatmap, get_monthly_completion
from utils.auth import authenticate_user, create_user, get_user_by_username, get_users, get_current_user
from utils.logger import setup_logger
from utils.models import get_session, Entry, Mood

logger = setup_logger()

MOOD_EMOJI = {
    'happy': '😊', 'excited': '🤩', 'calm': '😌', 'tired': '😴',
    'sad': '😢', 'angry': '😠', 'anxious': '😰', 'neutral': '😐'
}
MOOD_LABELS = {
    'happy': '开心', 'excited': '兴奋', 'calm': '平静', 'tired': '疲惫',
    'sad': '难过', 'angry': '生气', 'anxious': '焦虑', 'neutral': '一般'
}


class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录日记本")
        self.setFixedSize(350, 200)
        self.user_id = None
        self.username = None
        self.user_role = 'user'
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        layout.addWidget(self.username_input)

        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.password_input)

        button_layout = QHBoxLayout()
        self.login_btn = QPushButton("登录")
        self.login_btn.clicked.connect(self.do_login)
        self.register_btn = QPushButton("注册")
        self.register_btn.clicked.connect(self.do_register)
        button_layout.addWidget(self.login_btn)
        button_layout.addWidget(self.register_btn)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "错误", "请输入用户名和密码")
            return
        success, result = authenticate_user(username, password)
        if success:
            self.user_id = result['id']
            self.username = result['username']
            self.user_role = result.get('role', 'user')
            self.accept()
        else:
            QMessageBox.warning(self, "登录失败", result)

    def do_register(self):
        username = self.username_input.text().strip()
        password = self.password_input.text()
        if not username or not password:
            QMessageBox.warning(self, "错误", "请输入用户名和密码")
            return
        if len(username) < 3:
            QMessageBox.warning(self, "错误", "用户名至少3个字符")
            return
        if len(password) < 6:
            QMessageBox.warning(self, "错误", "密码至少6个字符")
            return
        success, msg = create_user(username, password)
        if success:
            QMessageBox.information(self, "成功", "注册成功，请登录")
        else:
            QMessageBox.warning(self, "注册失败", msg)


class EnhancedDiaryApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_user_id = 1
        self.current_username = "用户"
        self.current_role = 'user'
        self.current_date = get_today_str()
        self.last_save_time = datetime.now()
        self.current_mood = 'neutral'
        self.theme = 'light'

        self.init_ui()
        self.apply_theme()
        self.init_auto_save()
        self.load_entries()
        self.load_entry_content()
        self.update_streak_display()

    def init_ui(self):
        self.setWindowTitle(f"日记本 - {self.current_username}")
        self.setGeometry(100, 100, 1200, 800)

        self.create_menu_bar()
        self.create_central_widget()
        self.create_status_bar()

    def create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("文件")
        new_action = QAction("新建日记", self)
        new_action.triggered.connect(self.new_entry)
        save_action = QAction("保存", self)
        save_action.triggered.connect(lambda: self.save_entry(False))
        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self.delete_entry)
        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.close)
        file_menu.addActions([new_action, save_action, delete_action, exit_action])

        view_menu = menubar.addMenu("视图")
        self.theme_action = QAction("切换主题", self)
        self.theme_action.triggered.connect(self.toggle_theme)
        view_menu.addAction(self.theme_action)

        tools_menu = menubar.addMenu("工具")
        stats_action = QAction("统计", self)
        stats_action.triggered.connect(self.show_stats_dialog)
        challenges_action = QAction("写作挑战", self)
        challenges_action.triggered.connect(self.show_challenges_dialog)
        search_action = QAction("搜索", self)
        search_action.triggered.connect(self.show_search_dialog)
        habits_action = QAction("习惯分析", self)
        habits_action.triggered.connect(self.show_habits_dialog)
        tools_menu.addActions([stats_action, challenges_action, search_action, habits_action])

        admin_menu = menubar.addMenu("管理")
        user_mgmt_action = QAction("用户管理", self)
        user_mgmt_action.triggered.connect(self.show_user_management)
        migrate_action = QAction("数据迁移", self)
        migrate_action.triggered.connect(self.show_migration_dialog)
        admin_menu.addActions([user_mgmt_action, migrate_action])

        backup_menu = menubar.addMenu("备份")
        backup_action = QAction("备份管理", self)
        backup_action.triggered.connect(self.show_backup_dialog)
        backup_menu.addAction(backup_action)

    def create_central_widget(self):
        central = QWidget()
        main_layout = QHBoxLayout(central)

        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])

        main_layout.addWidget(splitter)
        self.setCentralWidget(central)

    def create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        title_label = QLabel(f"📔 {self.current_username} 的日记")
        title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        layout.addWidget(title_label)

        self.streak_label = QLabel("🔥 连续 0 天")
        self.streak_label.setFont(QFont("Arial", 10))
        layout.addWidget(self.streak_label)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索日记...")
        self.search_input.returnPressed.connect(self.quick_search)
        search_layout.addWidget(self.search_input)
        layout.addWidget(self.search_input)

        filter_label = QLabel("筛选标签:")
        layout.addWidget(filter_label)

        self.tag_filter = QComboBox()
        self.tag_filter.addItem("全部")
        self.tag_filter.currentTextChanged.connect(self.filter_by_tag)
        layout.addWidget(self.tag_filter)

        self.entries_list = QListWidget()
        self.entries_list.itemClicked.connect(self.on_entry_clicked)
        layout.addWidget(self.entries_list)

        return panel

    def create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        top_layout = QHBoxLayout()

        date_label = QLabel("日期:")
        top_layout.addWidget(date_label)
        self.date_edit = QDateEdit()
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.dateChanged.connect(self.on_date_changed)
        top_layout.addWidget(self.date_edit)

        mood_label = QLabel("心情:")
        top_layout.addWidget(mood_label)
        self.mood_combo = QComboBox()
        for mood, emoji in MOOD_EMOJI.items():
            self.mood_combo.addItem(f"{emoji} {MOOD_LABELS[mood]}", mood)
        self.mood_combo.currentIndexChanged.connect(self.on_mood_changed)
        top_layout.addWidget(self.mood_combo)

        top_layout.addStretch()

        self.save_btn = QPushButton("💾 保存")
        self.save_btn.clicked.connect(lambda: self.save_entry(False))
        top_layout.addWidget(self.save_btn)

        self.new_btn = QPushButton("📝 新建")
        self.new_btn.clicked.connect(self.new_entry)
        top_layout.addWidget(self.new_btn)

        layout.addLayout(top_layout)

        tag_layout = QHBoxLayout()
        tag_layout.addWidget(QLabel("标签:"))
        self.tag_input = QLineEdit()
        self.tag_input.setPlaceholderText("输入标签，用逗号分隔")
        tag_layout.addWidget(self.tag_input)
        layout.addLayout(tag_layout)

        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Microsoft YaHei", 12))
        layout.addWidget(self.text_edit)

        return panel

    def create_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def apply_theme(self):
        if self.theme == 'dark':
            self.setStyleSheet("""
                QWidget { background-color: #1e1e1e; color: #ffffff; }
                QTextEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d; }
                QListWidget { background-color: #2d2d2d; color: #ffffff; }
                QLineEdit { background-color: #2d2d2d; color: #ffffff; border: 1px solid #3d3d3d; }
                QComboBox { background-color: #2d2d2d; color: #ffffff; }
                QPushButton { background-color: #3d3d3d; color: #ffffff; border: none; padding: 5px 15px; }
                QPushButton:hover { background-color: #4d4d4d; }
            """)
        else:
            self.setStyleSheet("")

    def toggle_theme(self):
        self.theme = 'dark' if self.theme == 'light' else 'light'
        self.apply_theme()

    def init_auto_save(self):
        self.auto_save_timer = QTimer(self)
        self.auto_save_timer.timeout.connect(lambda: self.save_entry(True))
        config = get_config()
        if config.get('auto_save', True):
            interval = config.get('auto_save_interval', 30) * 1000
            self.auto_save_timer.start(interval)

    def load_entries(self):
        self.entries_list.clear()
        tag_data = get_tags()

        self.tag_filter.blockSignals(True)
        self.tag_filter.clear()
        self.tag_filter.addItem("全部")
        for tag in tag_data.keys():
            self.tag_filter.addItem(tag)
        self.tag_filter.blockSignals(False)

        entries = get_entries(self.current_user_id)
        for entry in entries:
            date_str = entry.stem
            item = QListWidgetItem(date_str)
            self.entries_list.addItem(item)

    def load_entry_content(self):
        try:
            timestamp, tags, content = get_entry_content(self.current_date, self.current_user_id)
            self.text_edit.setPlainText(content)
            self.tag_input.setText(", ".join(tags) if tags else "")

            mood_data = get_mood(self.current_date)
            if mood_data:
                self.current_mood = mood_data.get('mood_type', 'neutral')
                idx = self.mood_combo.findData(self.current_mood)
                if idx >= 0:
                    self.mood_combo.setCurrentIndex(idx)
        except Exception as e:
            logger.error(f"加载日记内容失败: {e}")

    def on_entry_clicked(self, item):
        self.current_date = item.text()
        year = int(self.current_date[:4])
        month = int(self.current_date[5:7])
        day = int(self.current_date[8:10])
        self.date_edit.setDate(QDate(year, month, day))
        self.load_entry_content()

    def on_date_changed(self, date):
        year = date.year()
        month = date.month()
        day = date.day()
        self.current_date = f"{year:04d}-{month:02d}-{day:02d}"
        self.load_entry_content()

    def on_mood_changed(self, index):
        self.current_mood = self.mood_combo.itemData(index)

    def save_entry(self, auto=False):
        content = self.text_edit.toPlainText()
        if not content.strip():
            return

        tags_str = self.tag_input.text().strip()
        tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]

        try:
            save_entry(self.current_date, content, tags, self.current_user_id)
            save_mood(self.current_date, self.current_mood, '')
            update_streak_on_entry(self.current_user_id, self.current_date)

            if not auto:
                self.load_entries()
                self.update_streak_display()
                self.status_bar.showMessage(f"日记已保存: {self.current_date}", 3000)
                logger.info(f"保存日记: {self.current_date}")

        except Exception as e:
            logger.error(f"保存日记失败: {e}")

    def new_entry(self):
        self.current_date = get_today_str()
        self.date_edit.setDate(QDate.currentDate())
        self.text_edit.clear()
        self.tag_input.clear()
        self.mood_combo.setCurrentIndex(7)
        self.status_bar.showMessage("新日记已创建", 2000)

    def delete_entry(self):
        if not self.current_date:
            QMessageBox.warning(self, "警告", "请先选择要删除的日记")
            return

        reply = QMessageBox.question(
            self, "确认", f"确定要删除 {self.current_date} 的日记吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            try:
                storage_delete_entry(self.current_date, self.current_user_id)
                self.load_entries()
                self.text_edit.clear()
                self.tag_input.clear()
                self.status_bar.showMessage(f"日记已删除: {self.current_date}", 3000)
                logger.info(f"删除日记: {self.current_date}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def update_streak_display(self):
        streak_info = get_user_streak_info(self.current_user_id)
        msg = get_streak_message(streak_info['current_streak'], streak_info['longest_streak'])
        self.streak_label.setText(msg)

    def quick_search(self):
        keyword = self.search_input.text().strip()
        if not keyword:
            self.load_entries()
            return

        self.entries_list.clear()
        entries = get_entries(self.current_user_id)
        for entry in entries:
            date_str = entry.stem
            timestamp, tags, content = get_entry_content(date_str, self.current_user_id)
            if keyword.lower() in content.lower() or keyword.lower() in ' '.join(tags).lower():
                item = QListWidgetItem(date_str)
                self.entries_list.addItem(item)

    def filter_by_tag(self, tag):
        self.entries_list.clear()
        entries = get_entries(self.current_user_id)
        for entry in entries:
            date_str = entry.stem
            timestamp, tags, content = get_entry_content(date_str, self.current_user_id)
            if tag == "全部" or tag in tags:
                item = QListWidgetItem(date_str)
                self.entries_list.addItem(item)

    def show_stats_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("统计信息")
        dialog.setFixedSize(600, 500)
        layout = QVBoxLayout(dialog)

        stats = get_diary_stats()
        tag_stats = get_tag_stats()

        info_label = QLabel(f"""
        <h2>📊 日记统计</h2>
        <p><b>日记总数:</b> {stats['total_diaries']}</p>
        <p><b>总字数:</b> {stats['total_words']}</p>
        <p><b>总字符数:</b> {stats['total_chars']}</p>
        <p><b>标签数量:</b> {len(tag_stats)}</p>
        """)
        layout.addWidget(info_label)

        if tag_stats:
            chart_label = QLabel("<h3>🏷️ 标签使用排行</h3>")
            layout.addWidget(chart_label)

            for i, stat in enumerate(tag_stats[:10], 1):
                layout.addWidget(QLabel(f"{i}. {stat['tag']} - {stat['count']} 篇"))

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def show_challenges_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("写作挑战")
        dialog.setFixedSize(500, 400)
        layout = QVBoxLayout(dialog)

        active = get_active_challenge(self.current_user_id)
        if active:
            layout.addWidget(QLabel(f"<h3>🔥 进行中: {active['name']}</h3>"))
            layout.addWidget(QLabel(f"目标: {active['target']} 天"))
            progress = QProgressBar()
            progress.setValue(int(active['progress'] / active['target'] * 100))
            layout.addWidget(progress)
            layout.addWidget(QLabel(f"已坚持: {active['progress']} 天"))
        else:
            layout.addWidget(QLabel("<h3>开始一个新的挑战吧！</h3>"))

            challenges = get_all_challenges_status(self.current_user_id)
            for cid, info in challenges.items():
                if not info['started']:
                    btn = QPushButton(f"开始 {info['name']} (需 {info['target']} 天)")
                    btn.clicked.connect(lambda checked, c=cid: self.start_challenge(c, dialog))
                    layout.addWidget(btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def start_challenge(self, challenge_id, dialog):
        start_challenge(self.current_user_id, challenge_id)
        QMessageBox.information(self, "成功", "挑战已开始！")
        dialog.close()
        self.show_challenges_dialog()

    def show_search_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("高级搜索")
        dialog.setFixedSize(500, 400)
        layout = QVBoxLayout(dialog)

        layout.addWidget(QLabel("关键词:"))
        keyword_input = QLineEdit()
        layout.addWidget(keyword_input)

        layout.addWidget(QLabel("开始日期:"))
        start_date = QDateEdit()
        start_date.setCalendarPopup(True)
        layout.addWidget(start_date)

        layout.addWidget(QLabel("结束日期:"))
        end_date = QDateEdit()
        end_date.setCalendarPopup(True)
        end_date.setDate(QDate.currentDate())
        layout.addWidget(end_date)

        layout.addWidget(QLabel("心情筛选:"))
        mood_filter = QComboBox()
        mood_filter.addItem("全部", "")
        for mood, emoji in MOOD_EMOJI.items():
            mood_filter.addItem(f"{emoji} {MOOD_LABELS[mood]}", mood)
        layout.addWidget(mood_filter)

        results_list = QListWidget()
        layout.addWidget(results_list)

        def do_search():
            results_list.clear()
            keyword = keyword_input.text().strip().lower()
            entries = get_entries(self.current_user_id)
            for entry in entries:
                date_str = entry.stem
                if start_date.date() > QDate(int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])):
                    continue
                if end_date.date() < QDate(int(date_str[:4]), int(date_str[5:7]), int(date_str[8:10])):
                    continue

                timestamp, tags, content = get_entry_content(date_str, self.current_user_id)
                mood_data = get_mood(date_str)
                selected_mood = mood_filter.itemData(mood_filter.currentIndex())

                if selected_mood and mood_data.get('mood_type') != selected_mood:
                    continue

                if keyword and keyword not in content.lower() and keyword not in ' '.join(tags).lower():
                    continue

                item = QListWidgetItem(f"{date_str} {' '.join([MOOD_EMOJI.get(mood_data.get('mood_type', 'neutral'), '😐')])} {tags}")
                item.setData(Qt.ItemDataRole.UserRole, date_str)
                results_list.addItem(item)

        search_btn = QPushButton("搜索")
        search_btn.clicked.connect(do_search)
        layout.addWidget(search_btn)

        results_list.itemDoubleClicked.connect(lambda item: self.open_entry_from_search(item, dialog))
        dialog.exec()

    def open_entry_from_search(self, item, dialog):
        date_str = item.data(Qt.ItemDataRole.UserRole)
        self.current_date = date_str
        year = int(date_str[:4])
        month = int(date_str[5:7])
        day = int(date_str[8:10])
        self.date_edit.setDate(QDate(year, month, day))
        self.load_entry_content()
        dialog.close()

    def show_habits_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("习惯分析")
        dialog.setFixedSize(600, 500)
        layout = QVBoxLayout(dialog)

        year = datetime.now().year
        heatmap = get_writing_heatmap(self.current_user_id, year)
        monthly = get_monthly_completion(self.current_user_id, year)

        layout.addWidget(QLabel(f"<h3>📅 {year} 年写作热力图</h3>"))
        layout.addWidget(QLabel(f"写作天数: {len(heatmap)}"))

        cal_label = QLabel("每月完成情况:")
        layout.addWidget(cal_label)

        for month, data in sorted(monthly.items()):
            layout.addWidget(QLabel(f"{month}: {data['days_written']}/{data['total_days']} 天 ({data['completion_rate']:.0%})"))

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.exec()

    def show_user_management(self):
        """显示用户管理界面"""
        if self.current_role not in ['admin', 'superadmin']:
            QMessageBox.warning(self, "警告", "只有管理员可以管理用户")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("用户管理")
        dialog.setFixedSize(600, 450)
        layout = QVBoxLayout(dialog)

        user_table = QTableWidget()
        user_table.setColumnCount(4)
        user_table.setHorizontalHeaderLabels(["ID", "用户名", "角色", "状态"])
        user_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(user_table)

        def refresh_users():
            session_db = get_session()
            from utils.models import User
            users = session_db.query(User).all()
            user_table.setRowCount(len(users))
            for row, user in enumerate(users):
                user_table.setItem(row, 0, QTableWidgetItem(str(user.id)))
                user_table.setItem(row, 1, QTableWidgetItem(user.username))
                user_table.setItem(row, 2, QTableWidgetItem(user.role))
                user_table.setItem(row, 3, QTableWidgetItem("正常" if user.is_active else "禁用"))

        def create_user_func():
            username, ok1 = QInputDialog.getText(dialog, "创建用户", "用户名：")
            if not ok1 or not username:
                return
            password, ok2 = QInputDialog.getText(dialog, "创建用户", "密码：", QLineEdit.EchoMode.Password)
            if not ok2 or not password:
                return

            from utils.auth import create_user
            role, ok3 = QInputDialog.getItem(dialog, "角色", "角色：", ["user", "admin", "superadmin"], 0)
            if not ok3:
                return

            try:
                create_user(username, password, role=role)
                refresh_users()
                QMessageBox.information(dialog, "成功", "用户创建成功")
                logger.info(f"创建用户: {username}")
            except Exception as e:
                QMessageBox.warning(dialog, "失败", f"创建用户失败：{str(e)}")

        def delete_user_func():
            selected = user_table.currentRow()
            if selected == -1:
                QMessageBox.warning(dialog, "警告", "请选择要删除的用户")
                return

            user_id = int(user_table.item(selected, 0).text())
            username = user_table.item(selected, 1).text()

            if user_id == self.current_user_id:
                QMessageBox.warning(dialog, "警告", "不能删除当前登录的用户")
                return

            reply = QMessageBox.question(dialog, "确认", f"确定要删除用户 {username} 吗？",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                session_db = get_session()
                from utils.models import User
                user = session_db.query(User).filter_by(id=user_id).first()
                if user:
                    session_db.delete(user)
                    session_db.commit()
                    refresh_users()
                    QMessageBox.information(dialog, "成功", "用户已删除")
                    logger.info(f"删除用户: {username}")

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(refresh_users)
        create_btn = QPushButton("创建用户")
        create_btn.clicked.connect(create_user_func)
        delete_btn = QPushButton("删除用户")
        delete_btn.clicked.connect(delete_user_func)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)

        btn_layout.addWidget(refresh_btn)
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        refresh_users()
        dialog.exec()

    def show_migration_dialog(self):
        """显示数据迁移界面"""
        if self.current_role not in ['admin', 'superadmin']:
            QMessageBox.warning(self, "警告", "只有管理员可以进行数据迁移")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("数据迁移")
        dialog.setFixedSize(550, 400)
        layout = QVBoxLayout(dialog)

        info_label = QLabel("<h3>文件系统 → 数据库迁移工具</h3>"
                           "<p>此工具将旧版日记文件迁移到数据库。</p>"
                           "<p>支持迁移：日记内容、标签、心情记录</p>")
        layout.addWidget(info_label)

        log_text = QTextEdit()
        log_text.setReadOnly(True)
        layout.addWidget(log_text)

        def log(message):
            log_text.append(message)

        def migrate_all():
            log_text.clear()
            log("=" * 40)
            log("开始迁移数据...")
            log("=" * 40)

            try:
                log("\n[1] 初始化数据库...")
                from utils.models import init_db
                init_db('sqlite:///diary.db')
                log("✓ 数据库初始化完成")

                log("\n[2] 初始化默认用户...")
                from utils.auth import init_users
                init_users()
                log("✓ 默认用户初始化完成")

                log("\n[3] 迁移日记条目...")

                session_db = get_session()
                from utils.storage import ENTRIES_DIR
                entries_dir = ENTRIES_DIR

                count = 0
                if entries_dir.exists():
                    entries_files = list(entries_dir.glob('*.txt'))
                    log(f"找到 {len(entries_files)} 个日记文件")

                    for entry_file in entries_files:
                        date_str = entry_file.stem

                        with open(entry_file, 'r', encoding='utf-8') as f:
                            content = f.read()

                        lines = content.split('\n')
                        timestamp = None
                        tags = []
                        content_lines = []

                        for line in lines:
                            if line.startswith('[') and ']' in line:
                                try:
                                    timestamp_str = line[1:-1]
                                    if ' ' in timestamp_str:
                                        from datetime import datetime
                                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    pass
                            elif line.startswith('Tags: '):
                                tag_str = line[6:].strip()
                                if tag_str:
                                    tags = [t.strip() for t in tag_str.split(',') if t.strip()]
                            else:
                                content_lines.append(line)

                        if not timestamp:
                            timestamp = datetime.now()

                        from utils.models import Entry, Tag
                        existing = session_db.query(Entry).filter_by(date_str=date_str, user_id=self.current_user_id).first()
                        if existing:
                            log(f"  {date_str} 已存在，跳过")
                            continue

                        entry = Entry(user_id=self.current_user_id, date_str=date_str,
                                     content='\n'.join(content_lines), timestamp=timestamp)
                        session_db.add(entry)
                        session_db.flush()

                        for tag_name in tags:
                            tag = session_db.query(Tag).filter_by(name=tag_name).first()
                            if not tag:
                                tag = Tag(name=tag_name)
                                session_db.add(tag)
                            entry.tags.append(tag)

                        session_db.commit()
                        count += 1
                        log(f"  ✓ 迁移成功: {date_str}")
                    log(f"✓ 日记条目迁移完成，共迁移 {count} 个")

                else:
                    log("  无日记目录，跳过")

                log("\n[4] 迁移心情记录...")
                from utils.mood import MOOD_FILE
                if MOOD_FILE.exists():
                    import json
                    with open(MOOD_FILE, 'r', encoding='utf-8') as f:
                        mood_data = json.load(f)

                    mood_count = 0
                    for date_str, record in mood_data.items():
                        from utils.models import Mood
                        existing_mood = session_db.query(Mood).filter_by(date_str=date_str, user_id=self.current_user_id).first()
                        if not existing_mood:
                            mood = Mood(user_id=self.current_user_id,
                                       date_str=date_str,
                                       mood_type=record.get('mood', 'neutral'),
                                       note=record.get('note', ''))
                            session_db.add(mood)
                            mood_count += 1
                    session_db.commit()
                    log(f"✓ 心情记录迁移完成，共迁移 {mood_count} 条")
                else:
                    log("  无心情记录文件，跳过")

                log("\n" + "=" * 40)
                log("迁移完成！")
                log("=" * 40)

                self.load_entries()
                QMessageBox.information(dialog, "成功", "数据迁移完成")

            except Exception as e:
                log(f"\n✗ 迁移失败: {str(e)}")
                QMessageBox.critical(dialog, "失败", f"数据迁移时发生错误: {str(e)}")

        btn_layout = QHBoxLayout()
        migrate_btn = QPushButton("开始迁移")
        migrate_btn.clicked.connect(migrate_all)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(migrate_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def show_backup_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("备份管理")
        dialog.setFixedSize(500, 400)
        layout = QVBoxLayout(dialog)

        backup_list = QListWidget()
        layout.addWidget(backup_list)

        def refresh_list():
            backup_list.clear()
            backups = list_backups()
            for timestamp, backup_dir in backups:
                size = sum(f.stat().st_size for f in backup_dir.rglob("*"))
                size_mb = size / (1024 * 1024)
                item = QListWidgetItem(f"{backup_dir.name} ({size_mb:.2f} MB)")
                item.setData(Qt.ItemDataRole.UserRole, backup_dir)
                backup_list.addItem(item)

        def create_backup():
            backup_entries()
            refresh_list()
            QMessageBox.information(dialog, "成功", "备份已创建")

        def restore_backup():
            item = backup_list.currentItem()
            if not item:
                QMessageBox.warning(dialog, "警告", "请选择要恢复的备份")
                return
            backup_dir = item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(dialog, "确认", "确定要恢复备份吗？这将覆盖当前数据。",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                restore_backup(backup_dir)
                self.load_entries()
                QMessageBox.information(dialog, "成功", "备份已恢复")

        def delete_backup():
            item = backup_list.currentItem()
            if not item:
                QMessageBox.warning(dialog, "警告", "请选择要删除的备份")
                return
            backup_dir = item.data(Qt.ItemDataRole.UserRole)
            reply = QMessageBox.question(dialog, "确认", "确定要删除备份吗？",
                                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                delete_backup(backup_dir)
                refresh_list()

        btn_layout = QHBoxLayout()
        create_btn = QPushButton("创建备份")
        create_btn.clicked.connect(create_backup)
        restore_btn = QPushButton("恢复备份")
        restore_btn.clicked.connect(restore_backup)
        delete_btn = QPushButton("删除备份")
        delete_btn.clicked.connect(delete_backup)
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(dialog.close)
        btn_layout.addWidget(create_btn)
        btn_layout.addWidget(restore_btn)
        btn_layout.addWidget(delete_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)

        refresh_list()
        dialog.exec()


def pyqt_mode():
    from utils.models import init_db
    from utils.storage import ensure_dir
    from utils.auth import init_users

    ensure_dir()
    try:
        init_db('sqlite:///diary.db')
        init_users()
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")

    app = QApplication(sys.argv)

    login = LoginDialog()
    if login.exec() != QDialog.DialogCode.Accepted:
        return

    window = EnhancedDiaryApp()
    window.current_user_id = login.user_id or 1
    window.current_username = login.username or "用户"
    window.current_role = login.user_role or 'user'
    window.setWindowTitle(f"日记本 - {window.current_username} ({window.current_role})")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    pyqt_mode()
