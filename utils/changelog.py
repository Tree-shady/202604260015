#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
软件更新日志模块
自动记录软件更新历史
"""

import json
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

CHANGELOG_FILE = Path("data") / "changelog.json"
VERSION_FILE = Path("data") / "version.json"

class Changelog:
    def __init__(self):
        self._ensure_files()

    def _ensure_files(self):
        """确保必要的文件存在"""
        CHANGELOG_FILE.parent.mkdir(exist_ok=True)
        if not CHANGELOG_FILE.exists():
            with open(CHANGELOG_FILE, 'w', encoding='utf-8') as f:
                json.dump([], f)
        if not VERSION_FILE.exists():
            self._init_version()

    def _init_version(self):
        """初始化版本文件"""
        version_info = {
            'version': '1.0.0',
            'build_date': datetime.now().isoformat(),
            'build_number': 1
        }
        with open(VERSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(version_info, f, ensure_ascii=False, indent=2)

    def _load_changelog(self) -> List[Dict]:
        """加载更新日志"""
        try:
            with open(CHANGELOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载更新日志失败: {e}")
            return []

    def _save_changelog(self, changelog: List[Dict]):
        """保存更新日志"""
        try:
            with open(CHANGELOG_FILE, 'w', encoding='utf-8') as f:
                json.dump(changelog, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存更新日志失败: {e}")

    def _load_version(self) -> Dict:
        """加载版本信息"""
        try:
            with open(VERSION_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载版本信息失败: {e}")
            return {'version': '0.0.0', 'build_date': '', 'build_number': 0}

    def _save_version(self, version_info: Dict):
        """保存版本信息"""
        try:
            with open(VERSION_FILE, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存版本信息失败: {e}")

    def _increment_build_number(self) -> int:
        """递增构建号"""
        version_info = self._load_version()
        new_build = version_info.get('build_number', 0) + 1
        version_info['build_number'] = new_build
        version_info['build_date'] = datetime.now().isoformat()
        self._save_version(version_info)
        return new_build

    def _bump_version(self, version_type: str = 'patch') -> str:
        """递增版本号"""
        version_info = self._load_version()
        current = version_info.get('version', '1.0.0')

        try:
            major, minor, patch = map(int, current.split('.'))
            if version_type == 'major':
                major += 1
                minor = 0
                patch = 0
            elif version_type == 'minor':
                minor += 1
                patch = 0
            else:
                patch += 1
            new_version = f"{major}.{minor}.{patch}"
        except:
            new_version = '1.0.0'

        version_info['version'] = new_version
        version_info['build_date'] = datetime.now().isoformat()
        self._save_version(version_info)
        return new_version

    def get_version(self) -> Dict:
        """获取当前版本信息"""
        return self._load_version()

    def get_changelog(self, limit: int = 20) -> List[Dict]:
        """获取更新日志"""
        changelog = self._load_changelog()
        return changelog[:limit]

    def add_entry(self, version: str, changes: Dict, change_type: str = 'patch') -> bool:
        """
        添加更新日志条目

        Args:
            version: 版本号（如不指定则自动递增）
            changes: 更新内容字典，格式：
                {
                    'added': ['新增功能1', '新增功能2'],
                    'fixed': ['修复问题1'],
                    'improved': ['优化1'],
                    'removed': ['移除功能1']
                }
            change_type: 版本类型 ('major', 'minor', 'patch')

        Returns:
            bool: 是否添加成功
        """
        try:
            if not version:
                version = self._bump_version(change_type)

            build_number = self._increment_build_number()

            entry = {
                'version': version,
                'build': build_number,
                'date': datetime.now().isoformat(),
                'changes': changes
            }

            changelog = self._load_changelog()
            changelog.insert(0, entry)

            self._save_changelog(changelog)

            logger.info(f"更新日志已记录: v{version} (build {build_number})")
            return True

        except Exception as e:
            logger.error(f"添加更新日志失败: {e}")
            return False

    def get_latest_changes(self) -> str:
        """获取最新版本的更新内容（Markdown格式）"""
        version_info = self._load_version()
        version = version_info.get('version', '1.0.0')
        changelog = self._load_changelog()

        if not changelog:
            return f"## v{version} (最新)\n\n暂无更新记录"

        latest = changelog[0]
        lines = [f"## v{latest['version']} ({latest['date'][:10]})"]
        lines.append(f"**Build #{latest.get('build', 1)}**\n")

        changes = latest.get('changes', {})

        if changes.get('added'):
            lines.append("### ✨ 新增功能")
            for item in changes['added']:
                lines.append(f"- {item}")
            lines.append("")

        if changes.get('fixed'):
            lines.append("### 🐛 问题修复")
            for item in changes['fixed']:
                lines.append(f"- {item}")
            lines.append("")

        if changes.get('improved'):
            lines.append("### ⚡ 功能优化")
            for item in changes['improved']:
                lines.append(f"- {item}")
            lines.append("")

        if changes.get('removed'):
            lines.append("### 🔥 移除功能")
            for item in changes['removed']:
                lines.append(f"- {item}")
            lines.append("")

        return "\n".join(lines)

    def export_markdown(self, output_path: str = "CHANGELOG.md") -> bool:
        """导出为Markdown格式"""
        try:
            changelog = self._load_changelog()
            version_info = self._load_version()

            lines = [
                "# 更新日志",
                "",
                f"**当前版本**: v{version_info.get('version', '1.0.0')}",
                f"**最后更新**: {version_info.get('build_date', '')[:10]}",
                "",
                "---",
                ""
            ]

            for entry in changelog:
                lines.append(f"## v{entry['version']} ({entry['date'][:10]})")
                lines.append(f"**Build #{entry.get('build', 1)}**\n")

                changes = entry.get('changes', {})

                if changes.get('added'):
                    lines.append("### ✨ 新增功能")
                    for item in changes['added']:
                        lines.append(f"- {item}")
                    lines.append("")

                if changes.get('fixed'):
                    lines.append("### 🐛 问题修复")
                    for item in changes['fixed']:
                        lines.append(f"- {item}")
                    lines.append("")

                if changes.get('improved'):
                    lines.append("### ⚡ 功能优化")
                    for item in changes['improved']:
                        lines.append(f"- {item}")
                    lines.append("")

                if changes.get('removed'):
                    lines.append("### 🔥 移除功能")
                    for item in changes['removed']:
                        lines.append(f"- {item}")
                    lines.append("")

                lines.append("---")
                lines.append("")

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(lines))

            logger.info(f"更新日志已导出到 {output_path}")
            return True

        except Exception as e:
            logger.error(f"导出更新日志失败: {e}")
            return False

changelog_manager = Changelog()

def record_update(changes: Dict, version: str = None, change_type: str = 'patch'):
    """记录更新的便捷函数"""
    return changelog_manager.add_entry(version, changes, change_type)

def get_current_version() -> str:
    """获取当前版本"""
    return changelog_manager.get_version().get('version', '1.0.0')

def get_changelog_html() -> str:
    """获取HTML格式的更新日志"""
    version_info = changelog_manager.get_version()
    entries = changelog_manager.get_changelog(10)

    html_parts = [
        f'<div class="changelog-header">',
        f'<h4>当前版本: v{version_info.get("version", "1.0.0")}</h4>',
        f'<p class="text-muted">最后更新: {version_info.get("build_date", "")[:10]}</p>',
        f'</div>',
        f'<div class="changelog-entries">'
    ]

    for entry in entries:
        date = entry['date'][:10]
        version = entry['version']
        build = entry.get('build', 1)
        changes = entry.get('changes', {})

        html_parts.append(f'<div class="changelog-entry">')
        html_parts.append(f'<h5>v{version} <small class="text-muted">({date}) Build #{build}</small></h5>')

        if changes.get('added'):
            html_parts.append('<ul class="list-unstyled"><li><strong>✨ 新增:</strong></li>')
            for item in changes['added']:
                html_parts.append(f'<li>&nbsp;&nbsp;- {item}</li>')
            html_parts.append('</ul>')

        if changes.get('fixed'):
            html_parts.append('<ul class="list-unstyled"><li><strong>🐛 修复:</strong></li>')
            for item in changes['fixed']:
                html_parts.append(f'<li>&nbsp;&nbsp;- {item}</li>')
            html_parts.append('</ul>')

        if changes.get('improved'):
            html_parts.append('<ul class="list-unstyled"><li><strong>⚡ 优化:</strong></li>')
            for item in changes['improved']:
                html_parts.append(f'<li>&nbsp;&nbsp;- {item}</li>')
            html_parts.append('</ul>')

        html_parts.append('</div>')

    html_parts.append('</div>')

    return '\n'.join(html_parts)
