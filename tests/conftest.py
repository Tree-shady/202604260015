"""Pytest 配置文件"""
import pytest
import sys
import os

# 添加上级目录到 Python 路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
