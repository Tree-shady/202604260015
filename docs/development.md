# 日记本应用开发文档

## 项目概述

这是一个基于 Flask 的个人日记本应用，提供日记撰写、标签管理、心情记录、数据统计等功能。

## 技术栈

- **后端框架**: Flask 3.0+
- **数据库**: SQLAlchemy + SQLite/PostgreSQL/MySQL
- **缓存**: Flask-Caching
- **前端**: HTML + CSS + JavaScript (Bootstrap 5)
- **用户认证**: Session-based + CSRF
- **密码安全**: PBKDF2-SHA256

## 项目结构

```
diary-app/
├── app.py                      # 应用入口（旧版本）
├── app_blueprints.py           # 应用入口（新版本，使用蓝图）
├── main.py                     # CLI 入口
├── migrate.py                  # 数据库迁移脚本
│
├── blueprints/                 # 蓝图模块
│   ├── __init__.py
│   ├── auth/                   # 认证蓝图
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── diary/                  # 日记蓝图
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── admin/                  # 管理蓝图
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── api/                    # API 蓝图
│   │   ├── __init__.py
│   │   └── routes.py
│   ├── settings/               # 设置蓝图
│   │   ├── __init__.py
│   │   └── routes.py
│   └── search/                 # 搜索蓝图
│       ├── __init__.py
│       └── routes.py
│
├── utils/                      # 工具模块
│   ├── models.py               # 数据库模型
│   ├── auth.py                # 认证模块
│   ├── validation.py          # 验证模块
│   ├── cache_manager.py       # 缓存管理
│   └── ...
│
├── templates/                  # Jinja2 模板
├── tests/                      # 测试文件
├── docs/                       # 文档
└── requirements.txt
```

## 环境配置

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```bash
# 必须配置
SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password

# 可选配置
FLASK_ENV=development
FLASK_PORT=5000
DATABASE_URL=sqlite:///diary.db
```

### 3. 启动应用

**开发模式**:

```bash
python app_blueprints.py
# 或
python -m flask run
```

**生产模式**:

```bash
export FLASK_ENV=production
python app_blueprints.py
```

## 数据库

### 模型关系

```
User (1) ----< (N) Entry
Entry (N) >----< (N) Tag
Entry (1) ---- (1) Mood
Entry (1) ----< (N) Image
Entry (1) >----< (N) Favorite
```

### 迁移

使用 SQLAlchemy 自动迁移：

```python
from utils.models import init_db, Base, engine

# 创建所有表
Base.metadata.create_all(engine)
```

## 认证流程

1. 用户提交用户名和密码
2. 使用 PBKDF2-SHA256 验证密码
3. 创建会话并设置 cookie
4. 会话超时时间：30分钟无活动
5. CSRF 保护：所有 POST 请求需要 CSRF token

## 缓存策略

应用使用 Flask-Caching 统一管理缓存：

```python
from utils.cache_manager import CacheManager, cached

# 方式1：直接使用
CacheManager.set('key', value, timeout=300)
value = CacheManager.get('key')

# 方式2：装饰器
@cached(timeout=300, key_prefix='view')
def get_expensive_data():
    ...
```

### 缓存键前缀

- `view:` - 视图函数缓存
- `query:` - 数据库查询缓存
- `user:` - 用户数据缓存

## 蓝图架构

应用使用 Flask 蓝图组织代码：

### 注册蓝图

```python
from blueprints.auth import auth_bp
from blueprints.diary import diary_bp
from blueprints.admin import admin_bp

app.register_blueprint(auth_bp)
app.register_blueprint(diary_bp)
app.register_blueprint(admin_bp)
```

### 蓝图 URL 前缀

| 蓝图 | 前缀 |
|------|------|
| auth | /auth |
| diary | / |
| admin | /admin |
| api | /api |
| settings | /settings |
| search | /search |

## 安全措施

### 1. 密码安全

- PBKDF2-SHA256 哈希
- 随机盐值
- 暴力破解防护（登录尝试限制）

### 2. 输入验证

- 日期格式验证
- 标签白名单验证
- XSS 防护（HTML 转义）
- CSRF 保护

### 3. 会话安全

- 安全 Cookie 设置
- 会话超时
- 密码过期机制

## 测试

### 运行测试

```bash
pytest tests/
```

### 运行覆盖率报告

```bash
pytest --cov=. tests/
```

### 编写新测试

在 `tests/` 目录下创建测试文件：

```python
import pytest

def test_example():
    assert True
```

## 日志

应用使用 Python logging 模块：

```python
import logging

logger = logging.getLogger(__name__)
logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
```

日志级别配置：

- `DEBUG` - 开发环境
- `INFO` - 信息
- `WARNING` - 警告
- `ERROR` - 错误

## 生产部署

### 使用 Gunicorn

```bash
gunicorn -w 4 -b 0.0.0.0:5000 app_blueprints:app
```

### Docker 部署

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "app_blueprints:app"]
```

## 性能优化

1. **数据库查询优化**
   - 使用 joinedload 预加载关联数据
   - 避免 N+1 查询
   - 添加数据库索引

2. **缓存优化**
   - 热点数据缓存
   - 缓存失效策略

3. **代码优化**
   - 减少重复代码
   - 统一错误处理
   - 合理使用装饰器

## 扩展开发

### 添加新功能

1. 在 `blueprints/` 下创建新蓝图
2. 定义路由和处理函数
3. 注册蓝图到应用
4. 添加相应的模板

### 添加新模型

1. 在 `utils/models.py` 中定义模型类
2. 运行迁移创建表
3. 添加相应的 CRUD 函数

### 添加新 API

1. 在 `blueprints/api/routes.py` 中添加路由
2. 实现业务逻辑
3. 添加适当的错误处理和日志
4. 编写测试

## 常见问题

### Q: 如何重置管理员密码？

A: 设置 `ADMIN_PASSWORD` 环境变量后重启应用。

### Q: 如何启用远程数据库？

A: 在设置页面配置 PostgreSQL 或 MySQL 连接信息。

### Q: 如何导出数据？

A: 使用导入/导出功能，支持 JSON、CSV、Markdown 格式。

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 编写代码和测试
4. 提交 Pull Request
5. 代码审查后合并

## 许可证

本项目采用 MIT 许可证。
