# 个人日记本

一个功能丰富的日记本应用，支持多种界面模式和标签系统。

## 功能特性

- ✍️ 写日记（支持今天或指定日期）
- 📖 阅读日记（Markdown 渲染 + 彩色输出）
- 📋 列出所有日记
- 🔍 搜索日记内容
- 🗑️ 删除日记
- 💾 退出时自动备份
- 🏷️ 标签系统（支持按标签分类）
- 🖥️ PyQt 图形化界面
- 🌐 Flask Web 界面（Bootstrap 响应式设计）

## Markdown 支持

日记内容支持 Markdown 格式，读取时以彩色终端输出：

| 语法 | 显示效果 |
|------|----------|
| `# 标题` | 绿色高亮标题 |
| `## 二级标题` | 绿色 |
| `### 三级标题` | 青色 |
| `**粗体**` | 黄色高亮 |
| `*斜体*` | 紫红色 |
| `- 列表项` | 带黄色圆点 |
| `> 引用` | 蓝色带竖线 |

## 安装依赖

```bash
pip install -r requirements.txt
```

## 运行方式

### 1. 终端模式
```bash
python main.py
```

### 2. PyQt 图形化界面
```bash
python pyqt_app.py
```

### 3. Flask Web 应用
```bash
python app.py
```
然后在浏览器中访问：http://127.0.0.1:5000

## 目录结构

```
.
├── main.py          # 终端版主程序
├── pyqt_app.py      # PyQt 图形化界面
├── app.py           # Flask Web 应用
├── entries/         # 日记存放目录
├── templates/       # Web 模板文件
│   ├── base.html    # 基础模板
│   ├── index.html   # 首页
│   ├── new.html     # 新建日记
│   ├── view.html    # 查看日记
│   ├── edit.html    # 编辑日记
│   └── tag.html     # 标签页面
├── tags.json        # 标签索引文件
├── requirements.txt # 依赖项列表
└── README.md
```

## 标签系统

- 在写日记时可以添加标签，多个标签用逗号分隔
- 标签会自动保存到 `tags.json` 文件中
- Web 界面支持按标签浏览日记
- PyQt 界面支持标签的添加和管理

## 数据备份

- 退出时会自动备份 `entries` 文件夹
- 备份文件格式：`entries_backup_年月日_时分秒`
