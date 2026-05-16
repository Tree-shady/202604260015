# 日记本应用 API 文档

## 概述

本文档描述了日记本应用的所有 REST API 端点。所有 API 都需要身份验证（通过会话 cookie）。

## 基础信息

- **基础URL**: `/api`
- **认证方式**: Session Cookie
- **响应格式**: JSON
- **字符编码**: UTF-8

## 认证 API

### 登录

**POST** `/auth/login`

用户登录系统。

**请求参数** (form-data):

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| username | string | 是 | 用户名 |
| password | string | 是 | 密码 |
| storage | string | 否 | 存储类型 (local/remote)，默认 local |

**响应示例**:

```json
{
  "success": true,
  "message": "登录成功"
}
```

### 注册

**POST** `/auth/register`

创建新用户账户。

**请求参数** (form-data):

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| username | string | 是 | 用户名 (3-50字符) |
| password | string | 是 | 密码 (至少8字符，包含大小写字母和数字) |
| confirm_password | string | 是 | 确认密码 |
| storage | string | 否 | 存储类型 |

**响应示例**:

```json
{
  "success": true,
  "message": "注册成功"
}
```

### 登出

**GET** `/auth/logout`

用户登出系统。

**响应示例**:

```json
{
  "success": true,
  "message": "已退出登录"
}
```

## 日记 API

### 获取日记列表

**GET** `/diary/index`

获取用户日记列表。

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| year | int | 否 | 年份 |
| month | int | 否 | 月份 |

**响应示例**:

```json
{
  "entries": [...],
  "total": 100
}
```

### 创建日记

**POST** `/diary/new`

创建新日记。

**请求参数** (form-data):

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| date | string | 是 | 日期 (YYYY-MM-DD) |
| content | string | 是 | 日记内容 |
| tags | string | 否 | 标签 (逗号分隔) |
| mood | string | 否 | 心情类型 |
| mood_note | string | 否 | 心情备注 |
| template | string | 否 | 模板ID |

**心情类型选项**:

- `happy` - 开心
- `excited` - 兴奋
- `calm` - 平静
- `tired` - 疲惫
- `sad` - 难过
- `angry` - 生气
- `anxious` - 焦虑
- `neutral` - 一般

### 查看日记

**GET** `/diary/entry/<date_str>`

查看指定日期的日记。

**路径参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| date_str | string | 日期 (YYYY-MM-DD) |

### 编辑日记

**POST** `/diary/edit/<date_str>`

编辑指定日期的日记。

**请求参数** (form-data):

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| date | string | 是 | 新日期 |
| content | string | 是 | 新内容 |
| tags | string | 否 | 标签 |
| mood | string | 否 | 心情类型 |
| mood_note | string | 否 | 心情备注 |

### 删除日记

**POST** `/diary/delete/<date_str>`

删除指定日期的日记。

## 通知 API

### 获取通知列表

**GET** `/api/notifications`

获取当前用户的通知列表。

**查询参数**:

| 参数 | 类型 | 必填 | 描述 |
|------|------|------|------|
| limit | int | 否 | 返回数量限制 (默认50) |
| unread_only | bool | 否 | 仅未读 (默认false) |

**响应示例**:

```json
{
  "notifications": [
    {
      "id": 1,
      "title": "日记保存成功",
      "message": "新日记已保存：2024-01-01",
      "level": "success",
      "read": false,
      "created_at": "2024-01-01T12:00:00"
    }
  ],
  "unread_count": 5
}
```

### 标记通知为已读

**POST** `/api/notifications/mark-read/<notification_id>`

### 标记所有通知为已读

**POST** `/api/notifications/mark-all-read`

### 删除通知

**DELETE** `/api/notifications/<notification_id>`

### 清空所有通知

**POST** `/api/notifications/clear`

## 收藏 API

### 获取收藏列表

**GET** `/api/favorites`

获取用户收藏的日记列表。

### 检查是否已收藏

**GET** `/api/favorites/<date_str>`

**响应示例**:

```json
{
  "favorited": true
}
```

### 添加收藏

**POST** `/api/favorites/<date_str>`

**请求头**:

| 参数 | 必填 | 描述 |
|------|------|------|
| X-CSRF-Token | 是 | CSRF 令牌 |

### 移除收藏

**DELETE** `/api/favorites/<date_str>`

## 写作提示 API

### 获取写作提示

**GET** `/api/prompts`

获取随机写作提示。

**查询参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| category | string | 提示分类 (daily/morning/night/weekend) |
| mood | string | 根据心情获取提示 |
| seasonal | bool | 是否使用季节性提示 |
| time_based | bool | 是否使用时间相关提示 |

**响应示例**:

```json
{
  "prompt": {
    "text": "今天最让你感恩的事情是什么？",
    "category": "daily"
  },
  "categories": ["daily", "morning", "night", "weekend"]
}
```

### 获取提示分类

**GET** `/api/prompts/categories`

### 批量获取提示

**GET** `/api/prompts/batch`

**查询参数**:

| 参数 | 类型 | 描述 |
|------|------|------|
| category | string | 提示分类 |
| count | int | 获取数量 (默认3) |

## 统计 API

### 获取统计数据

**GET** `/diary/stats`

获取用户日记统计数据。

**响应示例**:

```json
{
  "stats": {
    "total_entries": 100,
    "total_words": 50000,
    "total_chars": 250000,
    "total_tags": 20
  },
  "tag_stats": [
    {"tag": "工作", "count": 30},
    {"tag": "生活", "count": 25}
  ],
  "monthly_stats": [
    {"month": "2024-01", "count": 15}
  ],
  "mood_stats": {
    "happy": 40,
    "calm": 30,
    "neutral": 30
  },
  "mood_trend": [...]
}
```

## 错误响应

所有 API 错误都返回以下格式：

```json
{
  "error": "错误消息",
  "code": "ERROR_CODE"
}
```

### 常见错误码

| HTTP状态码 | 错误消息 | 描述 |
|------------|----------|------|
| 400 | 请求参数错误 | 参数格式或值不正确 |
| 401 | 需要登录 | 用户未登录或会话过期 |
| 403 | 权限不足 | 用户没有执行此操作的权限 |
| 404 | 资源不存在 | 请求的资源不存在 |
| 429 | 请求过于频繁 | 触发了速率限制 |
| 500 | 服务器内部错误 | 服务器发生错误 |

## 速率限制

部分 API 有速率限制：

| API 端点 | 限制 |
|----------|------|
| `/auth/login` | 10次/分钟 |
| `/auth/register` | 5次/3分钟 |
| `/api/favorites/*` | 20次/分钟 |
| `/api/notifications` | 30次/分钟 |

当触发速率限制时，返回 HTTP 429 状态码。
