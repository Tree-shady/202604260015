# 贡献指南

感谢你考虑为本项目贡献代码！

## 开发环境设置

1. Fork 并 clone 仓库

```bash
git clone https://github.com/Tree-shady/202604260015.git
cd 202604260015
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

## 代码风格

- 遵循 PEP 8
- 使用 black 格式化
- 使用 flake8 检查代码

## 提交规范

```
feat: 新功能
fix: 修复bug
docs: 文档更新
style: 代码格式调整
refactor: 重构代码
test: 测试相关
chore: 其他
```

## 提交 PR 流程

1. 创建功能分支
2. 进行修改
3. 提交更改
4. 推送到 Fork
5. 创建 Pull Request
