# Mario 帮你挑导师 — 广州大学机械与电气工程学院智能导师推荐系统

基于 **LangGraph** 构建的多 Agent 对话系统，通过自然语言交互为学生推荐研究生导师。

---

## 目录

- [项目概述](#项目概述)
- [技术栈](#技术栈)
- [系统架构](#系统架构)
- [核心功能](#核心功能)
- [项目结构](#项目结构)
- [模块详解](#模块详解)
  - [1. 多 Agent 工作流（LangGraph）](#1-多-agent-工作流langgraph)
  - [2. 用户画像系统](#2-用户画像系统)
  - [3. 导师推荐引擎](#3-导师推荐引擎)
  - [4. 缓存系统](#4-缓存系统)
  - [5. 用户认证系统](#5-用户认证系统)
  - [6. 前端界面](#6-前端界面)
  - [7. 日志系统](#7-日志系统)
- [部署方式](#部署方式)
- [环境变量](#环境变量)
- [本地开发](#本地开发)
- [API 接口](#api-接口)

---

## 项目概述

本项目是一个面向广州大学机械与电气工程学院的智能导师推荐系统，旨在帮助学生通过自然语言对话找到最适合自己的研究生导师。

**核心流程：**
1. 学生通过聊天告诉 Mario 自己的兴趣方向（如机器人、人工智能、嵌入式等）
2. 系统自动提取并构建用户画像（兴趣标签 + 目标标签）
3. 基于画像通过关键词匹配算法对全院导师进行评分排序
4. 以气泡卡片形式展示推荐导师列表，支持"换一批"功能
5. 支持查看/重置画像、探索方向、闲聊等交互

---

## 技术栈

| 类别 | 技术 | 用途 |
|------|------|------|
| **AI 框架** | LangGraph 0.2+ | 构建多 Agent 状态机工作流 |
| **LLM** | DeepSeek Chat API | 意图识别、画像提取、对话生成 |
| **Web 框架** | Flask 3.0+ | HTTP 服务、路由、模板渲染 |
| **数据库** | SQLite | 用户画像持久化、用户认证 |
| **前端** | HTML + CSS + JavaScript | 聊天界面、导师卡片浮窗 |
| **部署** | Render / Gunicorn | 生产环境部署 |
| **缓存** | 内存缓存（MemoryCache） | LLM 回复缓存、导师评分缓存 |

---

## 系统架构

```
用户输入
    │
    ▼
┌─────────────┐
│  intent_node │  ← 意图识别（LLM 分类）
│  (分类器)    │
└──────┬──────┘
       │
       ├──→ reset_profile  →  reset_profile_node  →  END
       │
       ├──→ explore        →  explore_node         →  END
       │
       ├──→ show_profile   →  show_profile_node    →  END
       │
       ├──→ update_profile →  profile_node → confirm_profile_node → END
       │
       ├──→ recommend      →  recommend_node       →  END
       │
       └──→ chat           →  chat_node            →  END
```

**工作流说明：**

系统基于 LangGraph 的 `StateGraph` 构建，每个节点是一个独立的 Agent 函数，通过条件边（`router`）根据意图识别结果路由到不同节点：

1. **intent_node** — 入口节点，使用 LLM 对用户输入进行意图分类
2. **profile_node** — 画像更新节点，调用 LLM 提取兴趣/目标标签
3. **confirm_profile_node** — 画像确认节点，生成确认回复
4. **show_profile_node** — 画像展示节点，生成画像分析报告
5. **recommend_node** — 导师推荐节点，调用推荐算法并返回结果
6. **explore_node** — 方向探索节点，介绍学院研究方向
7. **reset_profile_node** — 画像重置节点，清空用户画像
8. **chat_node** — 闲聊节点，注入导师信息支持问答

---

## 核心功能

### 1. 多 Agent 工作流（LangGraph）

**文件：** `app/agent/trying.py`

- 使用 LangGraph 的 `StateGraph` 构建有向图工作流
- 每个节点是一个独立的 Agent 函数，接收 `State` 并返回更新
- 通过 `router` 条件边实现动态路由
- 状态 `State` 包含：消息列表、用户输入、意图、画像、分析结果、回复等

**关键代码：**
```python
class State(TypedDict):
    messages: list[HumanMessage | AIMessage]   # 短期记忆
    user_input: str            # 当前输入
    intent: str                # 当前意图
    user_profile: Profile      # 长期特征
    analysis_result: dict      # 多agent分析结果
    approval: bool             # 导师是否审核通过
    response: str              # 助手回复
    next_step: str             # 流程位置
    session_id: str            # 会话ID，用于多用户隔离
```

### 2. 用户画像系统

**文件：** `app/agent/trying.py`（画像逻辑）、`app/profile_db.py`（数据库持久化）

**画像数据结构：**
```python
{
    "interest": {
        "机器人": {
            "score": 2.5,           # 累计分数
            "count": 3,             # 提及次数
            "positive_count": 3,    # 正面提及次数
            "negative_count": 0,    # 负面提及次数
            "last_update": "2024-01-15",
            "composite_score": 2.3  # 综合评分（含时间衰减）
        }
    },
    "goal": {
        "就业": { ... }
    },
    "history": [
        {"time": "2024-01-15", "message": "我喜欢机器人", "update": {...}}
    ]
}
```

**关键特性：**
- **正负权重支持**：用户说"不喜欢XXX"会生成负权重，降低匹配度
- **时间衰减**：`composite_score` 按 0.98 的衰减因子随时间降低
- **自动移除**：当 `composite_score < -0.1` 时自动移除该标签
- **中英文标签合并**：自动合并同义词（如 `ai` 和 `人工智能`）
- **自由文本标签**：支持用户自定义兴趣标签（不限于预定义列表）
- **SQLite 持久化**：使用 `profile_db.py` 模块进行数据库读写

**预定义兴趣标签（19个）：**
机器人、机械控制、人工智能、计算机视觉、嵌入式、智能制造、故障诊断、机械设计、微纳制造、车辆工程、材料工程、力学、传感检测、电力电子、智能电网、物联网、增材制造、流体力学、精密驱动

**预定义目标标签（6个）：**
就业、考研、读博、竞赛、创业、科研

### 3. 导师推荐引擎

**文件：** `app/retriever.py`

**评分算法：**
```
综合评分 = 研究方向匹配分 × 0.7 + 课程-目标匹配分 × 0.3
```

- **研究方向匹配**：通过关键词映射表（`KEYWORD_MAP`）匹配导师的研究方向和课程
- **课程-目标匹配**：根据导师课程名称与目标导向关键词的匹配程度评分
- **纯算法匹配**：不调用 LLM，毫秒级返回，避免超时
- **缓存支持**：评分结果缓存 10 分钟，画像更新时自动清除缓存

**关键词映射示例：**
```python
KEYWORD_MAP = {
    "robotics": ["机器人", "机器人技术", "仿生机器人", "外骨骼机器人", ...],
    "ai": ["人工智能", "机器学习", "深度学习", "强化学习", ...],
    "control": ["控制", "运动控制", "智能控制", "自适应控制", ...],
    ...
}
```

**推荐流程：**
1. 对所有导师进行评分排序，取前 30 个
2. 每次返回 6 个导师（支持"换一批"翻页）
3. 翻页循环：到达末尾后从头开始
4. 返回导师 JSON 数据供前端浮窗展示

### 4. 缓存系统

**文件：** `app/cache.py`

- **MemoryCache**：线程安全的内存缓存，支持 TTL
- **LLM 回复缓存**：相同输入 5 分钟内直接返回缓存
- **导师评分缓存**：评分结果缓存 10 分钟
- **缓存失效**：画像更新时自动清除该用户的导师评分缓存

### 5. 用户认证系统

**文件：** `app/user_db.py`

- **学号+姓名登录**：无需密码，自动注册/登录
- **Token 管理**：生成 64 位随机 token，有效期 7 天
- **会话隔离**：每个用户（session_id）拥有独立的画像和聊天历史
- **线程安全**：使用 `threading.Lock` 保证写入安全

### 6. 前端界面

**文件：** `app/templates/index.html`、`app/static/style.css`

**界面布局：**
- **左侧边栏**：Logo、功能介绍、使用提示
- **右侧主聊天区**：聊天头部、消息列表、输入区域

**交互功能：**
- **聊天气泡**：用户消息右对齐（蓝色渐变），机器人消息左对齐（白色）
- **打字机效果**：机器人回复逐字显示，带闪烁光标
- **加载动画**：三个跳动的小点表示正在生成回复
- **导师推荐浮窗**：点击"推荐导师"按钮弹出浮窗，以气泡卡片网格展示导师信息
- **画像浮窗**：点击"查看画像"按钮弹出浮窗，显示/刷新/重置画像
- **快捷输入**：提供"探索方向"、"查看画像"等快捷标签
- **响应式设计**：适配手机端，侧边栏折叠为横向布局

**导师卡片（气泡卡片样式）：**
- 头像（姓名首字）、姓名、匹配度
- 研究方向、课程、邮箱、主页链接
- 2 列网格布局，手机端 1 列

### 7. 日志系统

**文件：** `app/logger.py`

- 控制台输出 + 文件日志
- 按天分割日志文件
- 错误日志单独记录到 `error_*.log`

---

## 项目结构

```
gzhu_agent_web/
├── run.py                    # Flask 应用入口，路由定义
├── wsgi.py                   # WSGI 入口（生产部署）
├── render.yaml               # Render 部署配置
├── requirements.txt          # Python 依赖
├── .gitignore
├── app/
│   ├── agent/
│   │   └── trying.py         # LangGraph 多 Agent 工作流（核心）
│   ├── static/
│   │   └── style.css         # 前端样式（蓝色科技风格）
│   ├── templates/
│   │   ├── index.html        # 聊天主页面
│   │   └── login.html        # 登录页面
│   ├── cache.py              # 内存缓存模块
│   ├── gzhu_teachers.json    # 导师数据（JSON）
│   ├── logger.py             # 日志模块
│   ├── profile_db.py         # 用户画像数据库（SQLite）
│   ├── retriever.py          # 导师推荐引擎（关键词匹配）
│   └── user_db.py            # 用户认证数据库（SQLite）
└── logs/                     # 日志文件目录
```

---

## 部署方式

### Render 部署

`render.yaml` 配置：
```yaml
services:
  - type: web
    name: shy-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn wsgi:application --bind 0.0.0.0:$PORT --workers 1 --timeout 120 --max-requests 1
    envVars:
      - key: DEEPSEEK_API_KEY
        sync: false
```

**注意：**
- `--workers 1`：单 worker 避免 SQLite 并发问题
- `--timeout 120`：LLM 调用可能较慢，需要较长超时
- `--max-requests 1`：每个 worker 处理一个请求后重启，避免内存泄漏

### PythonAnywhere 部署

通过 `wsgi.py` 入口文件，在 Web 面板中配置 WSGI 路径指向此文件。

---

## 环境变量

| 变量名 | 说明 | 获取方式 |
|--------|------|----------|
| `DEEPSEEK_API_KEY` | DeepSeek API 密钥 | [platform.deepseek.com](https://platform.deepseek.com) |

---

## 本地开发

```bash
# 1. 克隆项目
git clone https://github.com/shysuhongyu-123/shy_agent.git
cd gzhu_agent_web

# 2. 安装依赖
pip install -r requirements.txt

# 3. 设置环境变量
# Windows:
set DEEPSEEK_API_KEY=your_api_key_here
# Linux/Mac:
export DEEPSEEK_API_KEY=your_api_key_here

# 4. 运行
python run.py

# 5. 访问
# http://127.0.0.1:5000
```

---

## API 接口

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 聊天主页面 |
| `/login` | GET | 登录页面 |
| `/api/login` | POST | 学号+姓名登录/注册 |
| `/api/verify` | POST | 验证 token 有效性 |
| `/api/logout` | POST | 登出 |
| `/welcome` | POST | 获取个性化欢迎消息 |
| `/chat` | POST | 发送聊天消息 |

**`/chat` 请求格式：**
```json
{
    "message": "我喜欢机器人",
    "session_id": "user_xxx"
}
```

**`/chat` 响应格式（普通回复）：**
```json
{
    "reply": "好的，我已记录您的兴趣：机器人。"
}
```

**`/chat` 响应格式（导师推荐）：**
```json
{
    "reply": "为您找到以下匹配导师：",
    "teachers": [
        {
            "name": "刘贵云",
            "score": "3.5",
            "research": ["机器人技术", "智能控制"],
            "courses": ["机器人学", "自动控制原理"],
            "email": "liugy@gzhu.edu.cn",
            "homepage": "http://example.com"
        }
    ]
}
```

---

## 技术亮点

1. **LangGraph 状态机**：使用有向图构建多 Agent 工作流，每个节点职责单一，易于扩展
2. **纯算法推荐**：导师匹配不依赖 LLM，毫秒级返回，避免超时和额外 API 费用
3. **动态画像系统**：支持正负权重、时间衰减、自动移除、中英文标签合并
4. **多级缓存**：LLM 回复缓存 + 导师评分缓存，大幅减少 API 调用
5. **多用户隔离**：基于 session_id 的独立画像和聊天历史
6. **打字机效果**：前端逐字显示回复，提升用户体验
7. **响应式设计**：完美适配手机端和桌面端