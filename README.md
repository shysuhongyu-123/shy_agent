# Mario 帮你挑导师 — 广州大学机械与电气工程学院智能导师推荐系统

基于 **LangGraph** 构建的多 Agent 对话系统，通过自然语言交互建立用户画像，智能推荐研究生导师。

---

## 目录

- [项目概述](#项目概述)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [核心功能](#核心功能)
- [技术点详解](#技术点详解)
  - [1. LangGraph 多 Agent 状态图](#1-langgraph-多-agent-状态图)
  - [2. 用户画像系统](#2-用户画像系统)
  - [3. 导师推荐算法](#3-导师推荐算法)
  - [4. 意图识别与路由](#4-意图识别与路由)
  - [5. 多级缓存系统](#5-多级缓存系统)
  - [6. SQLite 持久化存储](#6-sqlite-持久化存储)
  - [7. 用户认证系统](#7-用户认证系统)
  - [8. 前端交互设计](#8-前端交互设计)
  - [9. 日志系统](#9-日志系统)
  - [10. 生产部署](#10-生产部署)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [API 接口](#api-接口)

---

## 项目概述

本项目面向广州大学机械与电气工程学院的学生，通过对话式交互了解学生的兴趣方向（如机器人、人工智能、嵌入式等）和未来目标（如考研、就业、读博等），建立动态更新的用户画像，并基于画像智能推荐匹配的导师。

**核心创新点：**
- 使用 **LangGraph** 构建有向图状态机，实现多 Agent 协作
- 基于 **DeepSeek API** 的 LLM 驱动对话
- 纯算法匹配的导师推荐引擎（不依赖 LLM，毫秒级响应）
- 支持正负权重的动态画像更新机制
- 多用户隔离 + 会话级缓存

---

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| **Web 框架** | Flask 3.x | HTTP 服务、路由、模板渲染 |
| **AI Agent 框架** | LangGraph 0.2+ | 多 Agent 状态图编排 |
| **大语言模型** | DeepSeek Chat API | 意图识别、画像提取、对话生成 |
| **LLM 接口** | LangChain OpenAI | 统一 LLM 调用接口 |
| **前端** | HTML + CSS + JavaScript | 聊天界面、登录页面 |
| **数据库** | SQLite | 用户画像、认证信息持久化 |
| **缓存** | 内存缓存 (MemoryCache) | LLM 回复缓存、导师评分缓存 |
| **日志** | Python logging | 应用日志、错误日志 |
| **部署** | Gunicorn + Render | 生产部署 |
| **模板引擎** | Jinja2 | HTML 模板渲染 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                       用户浏览器                             │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ 登录页面     │  │ 聊天界面      │  │ 画像浮窗          │   │
│  │ login.html  │  │ index.html   │  │ profile-popup    │   │
│  └──────┬──────┘  └──────┬───────┘  └──────────────────┘   │
└─────────┼─────────────────┼─────────────────────────────────┘
          │                 │
          ▼                 ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flask Web 服务 (run.py)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ /api/login│  │ /chat    │  │ /welcome │  │ /api/verify│  │
│  │ /api/logout│  │ /        │  │          │  │            │  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └─────┬──────┘  │
└───────┼──────────────┼─────────────┼──────────────┼─────────┘
        │              │             │              │
        ▼              ▼             ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                    LangGraph Agent 引擎                       │
│                    app/agent/trying.py                       │
│                                                              │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │ intent   │───▶│ profile      │───▶│ confirm_profile  │   │
│  │ (意图识别)│    │ (画像更新)    │    │ (确认反馈)        │   │
│  └────┬─────┘    └──────────────┘    └──────────────────┘   │
│       │                                                      │
│       ├──▶ show_profile  (画像展示)                          │
│       ├──▶ recommend     (导师推荐)                          │
│       ├──▶ explore       (方向探索)                          │
│       ├──▶ reset_profile (画像重置)                          │
│       └──▶ chat          (闲聊/导师查询)                     │
└─────────────────────────────────────────────────────────────┘
        │              │             │              │
        ▼              ▼             ▼              ▼
┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐
│ user_db  │  │profile_db│  │ retriever│  │   cache      │
│ (用户认证)│  │ (画像存储)│  │ (推荐算法)│  │  (缓存模块)   │
└──────────┘  └──────────┘  └──────────┘  └──────────────┘
        │              │             │
        ▼              ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────────┐
│ users.db │  │profiles.db│  │ gzhu_teachers│
│ (SQLite) │  │ (SQLite)  │  │   .json      │
└──────────┘  └──────────┘  └──────────────┘
```

---

## 核心功能

1. **学号+姓名登录** — 无密码认证，自动注册/登录
2. **对话式画像建立** — 通过自然语言交互收集兴趣和目标
3. **智能导师推荐** — 基于画像的算法匹配，支持"换一批"
4. **画像管理** — 查看、刷新、重置画像
5. **方向探索** — 为迷茫学生介绍研究方向
6. **导师信息查询** — 支持查询具体导师信息
7. **多用户隔离** — 每个用户拥有独立画像和会话

---

## 技术点详解

### 1. LangGraph 多 Agent 状态图

**文件：** `app/agent/trying.py`

使用 **LangGraph** 构建有向图状态机，定义 `State` 类型包含消息列表、用户输入、意图、画像、分析结果等字段。

**状态图结构：**

```
intent (入口)
  ├──▶ update_profile → profile → confirm_profile → END
  ├──▶ show_profile → END
  ├──▶ recommend → END
  ├──▶ explore → END
  ├──▶ reset_profile → END
  └──▶ chat → END
```

**关键代码：**
```python
builder = StateGraph(State)
builder.add_node("intent", intent_node)
builder.add_node("profile", profile_node)
builder.add_node("confirm_profile", confirm_profile_node)
# ... 其他节点
builder.set_entry_point("intent")
builder.add_conditional_edges("intent", router, {...})
builder.add_edge("profile", "confirm_profile")
builder.add_edge("confirm_profile", END)
```

**技术要点：**
- `TypedDict` 定义强类型状态
- `add_conditional_edges` 实现意图路由
- 每个节点是独立的函数，接收 `State` 返回部分更新

---

### 2. 用户画像系统

**文件：** `app/agent/trying.py`

**画像数据结构：**
```python
{
    "interest": {
        "机器人": {
            "score": 2.5,          # 累计分数
            "count": 3,            # 提及次数
            "positive_count": 3,   # 正面提及次数
            "negative_count": 0,   # 负面提及次数
            "last_update": "2026-07-01",
            "composite_score": 2.1 # 综合评分（含时间衰减）
        }
    },
    "goal": { ... },  # 同上结构
    "history": [...]  # 对话历史
}
```

**核心机制：**

#### a) 画像提取 (`extract_profile`)
- 使用 LLM 从用户消息中提取兴趣和目标
- 支持中英文标签、自由文本标签
- 支持正负权重（"喜欢"→正权重，"不喜欢"→负权重）
- 支持上下文感知（结合最近对话判断指代）

#### b) 综合评分计算 (`compute_composite`)
```python
composite = (score * 0.6 + positive_count * 0.3 - negative_count * 0.2) * decay
```
- `decay = max(0.1, min(1.0, pow(0.98, days_diff)))` — 时间衰减
- 低于 `REMOVAL_THRESHOLD = -0.1` 的标签自动移除

#### c) 中英文标签合并
- 自动合并同义的中英文标签（如 `ai` ↔ `人工智能`）
- 保留中文标签，合并统计数据

---

### 3. 导师推荐算法

**文件：** `app/retriever.py`

**纯算法匹配，不调用 LLM，毫秒级响应。**

#### a) 关键词映射表 (`KEYWORD_MAP`)
- 19 个预定义兴趣标签，每个标签映射到 10-30 个中文关键词
- 覆盖机器人、控制、AI、视觉、嵌入式、智能制造等方向

#### b) 研究方向匹配
```python
research_score = 0
for profile_tag, info in user_profile["interest"].items():
    if profile_tag in KEYWORD_MAP:
        keywords = KEYWORD_MAP[profile_tag]
        if any(kw in text for kw in keywords):
            research_score += weight
    else:
        if profile_tag in text:  # 自由文本匹配
            research_score += weight
```

#### c) 课程-目标匹配 (`calculate_course_goal_score`)
- 就业导向：匹配"应用、技术、工程、设计"等关键词
- 考研导向：匹配"高等、理论、原理、力学"等关键词
- 读博/科研导向：匹配"前沿、研讨、论文、科研"等关键词
- 竞赛导向：匹配"创新、发明、设计、机器人"等关键词

#### d) 综合评分
```python
final_score = research_score * 0.7 + course_goal_score * 2.0 * 0.3
```

#### e) "换一批"机制
- 使用 `recommend_offset` 记录当前批次位置
- 每次推荐 6 个导师，支持循环翻页
- 偏移量持久化到 SQLite

---

### 4. 意图识别与路由

**文件：** `app/agent/trying.py` — `intent_node()`

使用 LLM 对用户输入进行意图分类，按优先级：

| 意图 | 触发条件 | 路由到 |
|------|----------|--------|
| `reset_profile` | 重置/清空/删除画像 | `reset_profile_node` |
| `explore` | 迷茫、想了解方向 | `explore_node` |
| `show_profile` | 查看画像 | `show_profile_summary_node` |
| `update_profile` | 表达个人兴趣/目标 | `profile_node` |
| `recommend` | 要求推荐/换一批 | `recommend_node` |
| `chat` | 闲聊/查询导师信息 | `chat_node` |

**特殊规则：**
- 查询"XX系有几位导师"等导师信息 → `chat`（不是 `update_profile`）
- 仅提到方向名称未表达偏好 → `chat`（不是 `update_profile`）

---

### 5. 多级缓存系统

**文件：** `app/cache.py`

基于线程安全的内存缓存，支持 TTL 过期。

| 缓存类型 | 键格式 | TTL | 用途 |
|----------|--------|-----|------|
| LLM 回复 | `llm:{session_id}:{md5(input)}` | 5 分钟 | 相同问题直接返回缓存 |
| 导师评分 | `teacher_score:{session_id}` | 10 分钟 | 避免重复计算评分 |
| 画像更新时 | 清除 `teacher_score:{session_id}` 和 `llm:{session_id}:*` | — | 保证数据一致性 |

**缓存类特性：**
- `threading.Lock` 保证线程安全
- `delete_pattern()` 支持前缀匹配删除
- `make_key()` 基于参数生成 MD5 缓存键

---

### 6. SQLite 持久化存储

#### 用户认证数据库 — `app/user_db.py`

**表结构：**
```sql
users (id, student_id, name, created_at, last_login)
sessions (token, user_id, created_at, expires_at)
```

**特性：**
- 学号唯一标识，无密码登录
- Token 有效期 7 天（`secrets.token_hex(32)`）
- `threading.Lock` 保证写入线程安全
- WAL 模式提高并发性能

#### 用户画像数据库 — `app/profile_db.py`

**表结构：**
```sql
profiles (session_id, interest, goal, recommend_offset, created_at, updated_at)
profile_history (id, session_id, time, message, intent, response, update_data)
```

**特性：**
- 画像以 JSON 字符串存储
- 支持 `ON CONFLICT` 的 UPSERT 操作
- 历史记录按时间倒序查询
- `check_recent_history` 避免重复记录

---

### 7. 用户认证系统

**流程：**
1. 用户输入学号+姓名 → `/api/login`
2. 学号不存在则自动注册，存在则验证姓名
3. 生成 64 位 hex token，有效期 7 天
4. 前端将 token 存入 `localStorage`
5. 每次请求携带 token → 服务端验证

**前端认证：**
- `getAuthToken()` — 从 localStorage 获取 token
- `checkAuth()` — 页面加载时验证登录状态
- `logout()` — 清除 token 并跳转登录页

---

### 8. 前端交互设计

**文件：** `app/templates/index.html` + `app/static/style.css`

#### 聊天界面
- 左侧边栏：Logo、操作指引、快捷提示
- 右侧主区：聊天消息、输入框、快捷按钮
- 响应式设计：桌面端双栏布局，移动端单栏

#### 交互特性
- **打字机效果** — LLM 回复逐字显示
- **加载动画** — 三个跳动小点
- **Markdown 渲染** — 将 LLM 回复中的 Markdown 转为 HTML
- **导师卡片** — 推荐结果以卡片样式展示
- **画像浮窗** — 点击"查看画像"弹出浮窗
- **快捷输入** — "探索方向"、"查看画像"等快捷标签
- **推荐按钮** — "推荐导师"和"换一批"按钮
- **发送防抖** — 防止快速重复提交

#### CSS 技术
- CSS 变量（`:root`）统一管理主题色
- `backdrop-filter: blur()` 毛玻璃效果
- `linear-gradient` 渐变背景和按钮
- `@keyframes` 动画（淡入、脉冲、跳动）
- 响应式媒体查询（768px 和 400px 断点）

---

### 9. 日志系统

**文件：** `app/logger.py`

- 控制台输出（stderr）
- 按天分割的文件日志（`logs/app_YYYY-MM-DD.log`）
- 错误日志单独文件（`logs/error_YYYY-MM-DD.log`）
- 日志格式：`时间 - 级别 - 模块 - 消息`

---

### 10. 生产部署

#### Render 部署 (`render.yaml`)
```yaml
services:
  - type: web
    name: shy-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:app --bind 0.0.0.0:$PORT --timeout 180
```

#### WSGI 入口 (`wsgi.py`)
- 兼容 gunicorn 和 PythonAnywhere
- 自动加载 `.env` 环境变量
- 支持 `wsgi:app` 和 `wsgi:application` 两种写法

#### 环境变量
- `DEEPSEEK_API_KEY` — DeepSeek API 密钥（必需）
- `FLASK_ENV=development` — 本地开发模式

---

## 项目结构

```
gzhu_agent_web/
├── run.py                    # Flask 应用入口，路由定义
├── wsgi.py                   # WSGI 生产部署入口
├── requirements.txt          # Python 依赖
├── render.yaml               # Render 部署配置
├── .env                      # 环境变量（API Key，不提交）
├── .gitignore                # Git 忽略规则
├── README.md                 # 本文件
│
├── app/
│   ├── agent/
│   │   └── trying.py         # LangGraph Agent 引擎（核心）
│   │
│   ├── static/
│   │   └── style.css         # 前端样式
│   │
│   ├── templates/
│   │   ├── index.html        # 聊天主页面
│   │   └── login.html        # 登录页面
│   │
│   ├── cache.py              # 内存缓存模块
│   ├── logger.py             # 日志模块
│   ├── profile_db.py         # 画像 SQLite 存储
│   ├── retriever.py          # 导师推荐算法
│   ├── user_db.py            # 用户认证数据库
│   └── gzhu_teachers.json    # 导师数据（JSON）
│
└── logs/                     # 日志文件目录
    ├── app_YYYY-MM-DD.log
    └── error_YYYY-MM-DD.log
```

---

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/shysuhongyu-123/shy_agent.git
cd gzhu_agent_web
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 设置 API Key
```bash
# Windows
set DEEPSEEK_API_KEY=your_api_key_here

# 或创建 .env 文件
echo DEEPSEEK_API_KEY=your_api_key_here > .env
```

### 4. 运行
```bash
python run.py
```

访问 `http://127.0.0.1:5000` 即可使用。

---

## API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 聊天主页面 |
| `/login` | GET | 登录页面 |
| `/api/login` | POST | 学号+姓名登录/注册 |
| `/api/verify` | POST | 验证 token 有效性 |
| `/api/logout` | POST | 登出 |
| `/welcome` | POST | 获取欢迎引导消息 |
| `/chat` | POST | 发送聊天消息 |

---

## 许可证

本项目为广州大学机械与电气工程学院课程设计作品。