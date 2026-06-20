import os
import sys
from typing import TypedDict
from datetime import datetime
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import json

from app.retriever import recommend_teachers
from app.profile_db import (
    load_profile as db_load_profile,
    save_profile as db_save_profile,
    add_history as db_add_history,
    check_recent_history as db_check_recent_history
)
from app.logger import logger
from app.cache import invalidate_teacher_scores

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY")
if not DEEPSEEK_API_KEY:
    raise ValueError(
        "请设置环境变量 DEEPSEEK_API_KEY。\n"
        "本地开发：在终端执行 set DEEPSEEK_API_KEY=你的密钥\n"
        "PythonAnywhere：在 Web 面板的 Environment variables 中添加"
    )
os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_API_KEY

INTEREST_MAP = {
    "robotics": "机器人",
    "control": "机械控制",
    "ai": "人工智能",
    "vision": "计算机视觉",
    "embedded": "嵌入式",
    "smart_manufacturing": "智能制造",
    "fault_diagnosis": "故障诊断",
    "mechanical_design": "机械设计",
    "micro_nano": "微纳制造",
    "vehicle": "车辆工程",
    "materials": "材料工程",
    "mechanics": "力学",
    "sensing": "传感检测",
    "power_electronics": "电力电子",
    "smart_grid": "智能电网",
    "iot": "物联网",
    "additive_manufacturing": "增材制造",
    "fluid_mechanics": "流体力学",
    "precision_drive": "精密驱动"
}

# 目标标签（职业/学业规划）
GOAL_MAP = {
    "employment": "就业",
    "master": "考研",
    "phd": "读博",
    "competition": "竞赛",
    "entrepreneurship": "创业",
    "research": "科研"
}

# 中文名称映射（用于显示）
NAME_MAP = {}
NAME_MAP.update(INTEREST_MAP)
NAME_MAP.update(GOAL_MAP)


class Profile(TypedDict):
    interest: dict
    goal: dict
    history: list


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


def create_llm():
    return ChatOpenAI(
        model="deepseek-chat",
        base_url="https://api.deepseek.com",
        api_key=DEEPSEEK_API_KEY,
        temperature=0.7,
        max_tokens=2048
    )


llm = create_llm()


def load_all_teachers():
    """加载所有导师数据，供 chat_node 和 recommend_node 使用"""
    import json as _json
    # 项目根目录：BASE_DIR 是 app/agent/，根目录是 app/agent/../../ (即项目根)
    project_root = os.path.dirname(os.path.dirname(BASE_DIR))  # app/agent/ -> app/ -> 项目根
    teachers_path = os.path.join(project_root, "app", "gzhu_teachers.json")
    # 备用路径
    if not os.path.exists(teachers_path):
        teachers_path = os.path.join(project_root, "gzhu_teachers.json")
    try:
        with open(teachers_path, "r", encoding="utf-8") as f:
            teachers = _json.load(f)
        return teachers
    except Exception as e:
        print("加载导师数据失败:", e)
        return []


# 全局缓存所有导师数据
ALL_TEACHERS = load_all_teachers()


def intent_node(state: State):
    prompt = f"""你是一个意图分类器。根据用户输入，只返回以下词之一：
    - reset_profile：用户想重置/清空/删除画像（如"重置我的画像"、"清空画像"、"重新开始"、"删除画像"、"重置"）。注意：这是最高优先级，只要用户表达重置意图就返回此值。
    - explore：用户表示迷茫、不知道喜欢什么、想了解各个方向、让系统介绍研究方向（如"我不知道喜欢什么"、"给我介绍一下方向"、"有哪些方向"、"我不知道选什么"、"我不确定"、"帮我看看"、"介绍方向"）。
    - show_profile：用户提及查看画像及其类似语义（如"查看画像"、"我的画像"、"看看我的兴趣"、"当前画像"、"查看用户画像"）。
    - update_profile：用户表达了个人兴趣、目标、计划、专业背景、喜好（如"我喜欢..."、"我想..."、"我计划..."），需要记录到用户画像。
    - recommend：用户在寻求建议、推荐导师、方向或资源（前提是画像已更新或无需更新）。注意：用户说"换一批"、"换几个"、"换一些"、"换导师"、"换推荐"等也属于 recommend。
    - chat：普通闲聊、问候、或无法归入以上几类的问题。
    分类规则（按优先级从高到低）：
    1. 如果用户明确表达重置/清空/删除画像的意图，返回 reset_profile
    2. 如果用户表示迷茫、不知道喜欢什么、想了解方向，返回 explore
    3. 如果用户想查看画像，返回 show_profile
    4. 如果用户表达了个人兴趣/目标/喜好（即使是以否定形式如"不喜欢"），返回 update_profile
    5. 如果用户明确要求推荐，返回 recommend
    6. 其他情况返回 chat

    重要判断规则：
    - 如果用户是在询问某个系/学院/专业有哪些导师、几位导师、导师信息（如"智能工程系有几位硕士导师"、"网络安全方面的导师"、"机械设计专业的老师"），这属于查询导师信息，应返回 chat（因为 chat_node 可以回答导师相关问题）
    - 只有当用户明确表达"我喜欢/我想/我感兴趣/我计划/我的兴趣是"等个人偏好时，才返回 update_profile
    - 如果用户只是提到某个方向名称但没有表达个人偏好（如"网络安全方向"、"机器人方向"），不应视为 update_profile

    用户输入：{state['user_input']}

    只返回一个词，不要解释。"""
    response = llm.invoke(prompt)
    intent = response.content.strip().lower()
    if intent not in ("show_profile", "update_profile", "recommend", "chat", "explore", "reset_profile"):
        intent = "chat"
    logger.info("意图识别: %s", intent)
    return {"intent": intent}


def load_profile(session_id: str = "default") -> dict:
    """从 SQLite 数据库加载用户画像"""
    return db_load_profile(session_id)


def save_profile(profile: dict, session_id: str = "default"):
    """保存用户画像到 SQLite 数据库"""
    db_save_profile(session_id, profile)


def extract_profile(message):
    # 构建兴趣标签列表供 LLM 参考（仅作为示例，不限制输出）
    interest_options = ", ".join([f"{k}({v})" for k, v in INTEREST_MAP.items()])
    goal_options = ", ".join([f"{k}({v})" for k, v in GOAL_MAP.items()])

    prompt = f"""
提取用户画像信息：
用户输入:
{message}

预定义的兴趣标签（仅作参考，不强制使用）：
{interest_options}

预定义的目标标签（仅作参考，不强制使用）：
{goal_options}

规则：
1. 支持一次消息提到多个兴趣/目标
2. **重要：如果用户说的兴趣不在预定义列表中，请使用用户的原话作为 name（中文），并设置 weight。** 例如用户说"我喜欢数字媒体"，则输出 {{"name":"数字媒体","weight":1.0}}
3. **重要：如果用户说"像XXX啊，XXX这些"、"比如XXX、XXX"、"例如XXX"等列举具体方向，请把每个具体方向都作为独立的兴趣提取，不要合并到预定义标签中。** 例如用户说"像强化学习啊，深度学习这些"，应输出 {{"name":"强化学习","weight":1.0}} 和 {{"name":"深度学习","weight":1.0}}，而不是只输出 {{"name":"ai","weight":1.0}}
4. 支持正负权重，**特别注意否定表达**：
   - "喜欢/有兴趣/感兴趣/想学/想了解" => 正权重 0.2~1.0
   - **"不喜欢/没兴趣/不考虑/不想学/不感兴趣/不喜欢了/不想"** => 负权重 -0.5~-1.0
   - **"我又不喜欢XXX了"、"我不喜欢XXX了"、"对XXX没兴趣了"** => 负权重 -1.0
   - "不想就业/放弃就业/不考虑就业" => employment:-1
5. **重要：如果用户说"不喜欢XXX"，必须提取为负权重，不能提取为正权重！**
6. 输出格式必须严格如下 JSON：
{{
  "interests": [
    {{"name":"robotics","weight":1.0}},
    {{"name":"数字媒体","weight":1.0}},
    {{"name":"ai","weight":0.8}}
  ],
  "goals": [
    {{"name":"phd","weight":1.0}}
  ]
}}
7. 如果消息没有提到兴趣或目标，则返回空数组
8. 只返回 JSON，不要解释、不要额外文本
"""
    response = llm.invoke(prompt)
    logger.info("画像提取结果: %s", response.content[:200])
    try:
        return json.loads(response.content)
    except Exception as e:
        logger.error("JSON解析失败: %s", str(e))
        return {
            "interests": [],
            "goals": []
        }


def compute_composite(score, positive_count, negative_count, last_update):
    days_diff = (datetime.now() - datetime.strptime(last_update, "%Y-%m-%d")).days
    decay = max(0.1, min(1.0, pow(0.98, days_diff)))
    composite = (score * 0.6 + positive_count * 0.3 - negative_count * 0.2) * decay
    return round(composite, 2)


def update_profile(profile, message):
    profile_info = extract_profile(message)
    now = datetime.now().strftime("%Y-%m-%d")

    # 删除阈值：当 composite_score 低于此值时移除该标签
    # 一次"不喜欢"（权重-1.0）即可触发删除
    REMOVAL_THRESHOLD = -0.1

    for item in profile_info.get("interests", []):
        name = item["name"]
        weight = item.get("weight", 1.0)
        is_positive = weight >= 0
        if name not in profile["interest"]:
            profile["interest"][name] = {
                "score": weight,
                "count": 1,
                "positive_count": 1 if is_positive else 0,
                "negative_count": 0 if is_positive else 1,
                "last_update": now,
                "composite_score": weight
            }
        else:
            entry = profile["interest"][name]
            entry["score"] += weight
            entry["count"] += 1
            if is_positive:
                entry["positive_count"] += 1
            else:
                entry["negative_count"] += 1
            entry["last_update"] = now
            entry["composite_score"] = compute_composite(
                entry["score"],
                entry["positive_count"],
                entry["negative_count"],
                entry["last_update"]
            )
            # 如果 composite_score 低于阈值，移除该标签
            if entry["composite_score"] < REMOVAL_THRESHOLD:
                del profile["interest"][name]
    for item in profile_info.get("goals", []):
        name = item["name"]
        weight = item.get("weight", 1.0)
        is_positive = weight >= 0
        if name not in profile["goal"]:
            profile["goal"][name] = {
                "score": weight,
                "count": 1,
                "positive_count": 1 if is_positive else 0,
                "negative_count": 0 if is_positive else 1,
                "last_update": now,
                "composite_score": weight
            }
        else:
            entry = profile["goal"][name]
            entry["score"] += weight
            entry["count"] += 1
            if is_positive:
                entry["positive_count"] += 1
            else:
                entry["negative_count"] += 1
            entry["last_update"] = now
            entry["composite_score"] = compute_composite(
                entry["score"],
                entry["positive_count"],
                entry["negative_count"],
                entry["last_update"]
            )
            # 如果 composite_score 低于阈值，移除该标签
            if entry["composite_score"] < REMOVAL_THRESHOLD:
                del profile["goal"][name]
    profile["history"].append({"time": now, "message": message, "update": profile_info})
    profile["history"] = profile["history"][-50:]
    return profile, profile_info  # 返回提取结果，用于动态确认


def profile_node(state: State):
    profile, profile_info = update_profile(state["user_profile"], state["user_input"])
    logger.info("画像更新后: %s", str({k: list(v.keys()) for k, v in profile.items() if isinstance(v, dict)}))
    # 画像更新了，清除该用户的导师评分缓存
    session_id = state.get("session_id", "default")
    invalidate_teacher_scores(session_id)
    # 将提取的信息暂存到 analysis_result，供 confirm 使用
    return {
        "user_profile": profile,
        "analysis_result": profile_info  # 包含 interests / goals 列表
    }


def confirm_profile_node(state: State):
    """根据实际更新的内容生成确认语，区分正负权重"""
    info = state.get("analysis_result", {})
    interests = info.get("interests", [])
    goals = info.get("goals", [])

    parts = []
    if interests:
        for i in interests:
            name = NAME_MAP.get(i["name"], i["name"])
            weight = i.get("weight", 1.0)
            if weight >= 0:
                parts.append(f"兴趣：{name}")
            else:
                parts.append(f"不喜欢：{name}")
    if goals:
        for g in goals:
            name = NAME_MAP.get(g["name"], g["name"])
            weight = g.get("weight", 1.0)
            if weight >= 0:
                parts.append(f"目标：{name}")
            else:
                parts.append(f"不喜欢：{name}")

    if parts:
        confirm_text = "好的，我已记录您的" + "，".join(parts) + "。"
    else:
        confirm_text = "好的，我已记录您的偏好。"

    # 维护消息列表
    messages = state.get("messages", []) + [
        HumanMessage(content=state["user_input"]),
        AIMessage(content=confirm_text)
    ]

    return {
        "response": confirm_text,
        "messages": messages,
        "intent": "update_profile"  # 保留 intent 供 run_agent 判断
    }


def get_sorted_profile(profile_dict):
    return sorted(
        profile_dict.items(),
        key=lambda x: x[1].get("composite_score", 0),
        reverse=True
    )


def build_profile_summary(profile):
    interests = get_sorted_profile(profile["interest"])
    goals = get_sorted_profile(profile["goal"])
    # 翻译为中文
    interest_text = [f"{NAME_MAP.get(name, name)}({data['composite_score']})" for name, data in interests]
    goals_text = [f"{NAME_MAP.get(name, name)}({data['composite_score']})" for name, data in goals]
    return f"""
    用户兴趣排序：
    {", ".join(interest_text)}
    用户目标排序：
    {", ".join(goals_text)}"""


def get_top_items(items_dict, top_n=2):
    sorted_items = sorted(items_dict.items(), key=lambda x: x[1].get("composite_score", 0), reverse=True)
    return sorted_items[:top_n]


def get_latest_update(history):
    if not history:
        return None
    for record in reversed(history):
        update = record.get("update", {})
        if isinstance(update, dict):
            interests = update.get("interests", [])
            goals = update.get("goals", [])
            if interests or goals:
                return record
        elif isinstance(update, str) and update:
            # 如果是 JSON 字符串，尝试解析
            try:
                import json
                parsed = json.loads(update)
                if parsed.get("interests") or parsed.get("goals"):
                    return record
            except Exception:
                pass
    return None


def build_profile_brief(profile):
    """生成中文摘要，用于推荐 prompt"""
    if not profile:
        return "用户画像空"
    interests = get_top_items(profile.get("interest", {}))
    goals = get_top_items(profile.get("goal", {}))
    latest_update = get_latest_update(profile.get("history", []))
    history_count = len(profile.get("history", []))

    text = "用户画像\n\n"
    text += "核心兴趣：\n"
    if interests:
        for idx, (name, data) in enumerate(interests, 1):
            text += f"① {NAME_MAP.get(name, name)} ({data.get('composite_score', 0)})\n"
    else:
        text += "暂无兴趣\n"
    text += "\n当前目标：\n"
    if goals:
        for idx, (name, data) in enumerate(goals, 1):
            text += f"① {NAME_MAP.get(name, name)} ({data.get('composite_score', 0)})\n"
    else:
        text += "暂无目标\n"
    text += "\n最近更新：\n"
    if latest_update:
        text += f"{latest_update['message']}\n"
    else:
        text += "暂无更新记录\n"
    text += f"\n历史交互：{history_count}条\n"
    user_tendencies = []
    if interests:
        user_tendencies.append(" ".join([NAME_MAP.get(name, name) for name, _ in interests]))
    if goals:
        user_tendencies.append(" ".join([NAME_MAP.get(name, name) for name, _ in goals]))
    if user_tendencies:
        text += "\n用户倾向：\n" + "、".join(user_tendencies)
    return text


def show_profile_summary_node(state: State):
    # 从数据库读取最新的画像数据，确保展示的是持久化的最新内容
    session_id = state.get("session_id", "default")
    profile = load_profile(session_id)

    interests = get_sorted_profile(profile["interest"])
    goals = get_sorted_profile(profile["goal"])

    # 如果画像为空，直接返回提示
    if not interests and not goals:
        reply = "您还没有记录任何画像信息哦！可以告诉我您的兴趣方向（比如机器人、人工智能、嵌入式等）和未来目标（比如考研、就业等），我来帮您建立画像。"
        messages = state.get("messages", []) + [
            HumanMessage(content=state["user_input"]),
            AIMessage(content=reply)
        ]
        return {
            "response": reply,
            "messages": messages
        }

    interest_text = "\n".join([
        f"{NAME_MAP.get(name, name)}（{data['composite_score']}）"
        for name, data in interests[:3]
    ])

    goal_text = "\n".join([
        f"{NAME_MAP.get(name, name)}（{data['composite_score']}）"
        for name, data in goals[:3]
    ])

    prompt = f"""
你是一名用户画像分析专家。用户兴趣：{interest_text}用户目标：{goal_text}请生成：核心兴趣：xxx说明：xxx目标：xxx说明：xxx要求：
1 中文输出
2 不超过200字
3 像导师分析学生一样
4 不要出现JSON
5 不要出现编号
"""
    response = llm.invoke(prompt)

    # 维护消息
    messages = state.get("messages", []) + [
        HumanMessage(content=state["user_input"]),
        AIMessage(content=response.content)
    ]

    return {
        "response": response.content,
        "messages": messages
    }


def recommend_node(state: State):
    """推荐导师，每次返回6个，支持换一批"""
    session_id = state.get("session_id", "default")
    profile = load_profile(session_id)

    try:
        # 打印画像信息用于调试
        logger.info("推荐导师: session=%s, interest=%s, goal=%s",
                     session_id,
                     list(profile.get('interest', {}).keys()),
                     list(profile.get('goal', {}).keys()))

        # 1. 用推荐算法对所有导师打分排序，取前30个（带缓存）
        all_scored = recommend_teachers(profile, top_n=30, session_id=session_id)
        logger.info("推荐导师: 候选数量=%d", len(all_scored))

        if not all_scored:
            logger.warning("推荐导师: 没有匹配到任何导师！")
            reply = "抱歉，暂时没有匹配到合适的导师。您可以先告诉我您的兴趣方向，我来帮您匹配。"
            messages = state.get("messages", []) + [
                HumanMessage(content=state["user_input"]),
                AIMessage(content=reply)
            ]
            return {"response": reply, "messages": messages}

        # 2. 判断是否是"换一批"请求
        user_input = state.get("user_input", "")
        is_refresh = any(kw in user_input for kw in ["换一批", "换几个", "换一些", "换导师", "换推荐", "换人", "换"])

        # 3. 从 session 中获取已推荐的导师索引
        from app.profile_db import get_recommend_offset, set_recommend_offset
        try:
            offset = get_recommend_offset(session_id)
        except Exception:
            offset = 0

        if is_refresh:
            offset += 6  # 跳过上一批
        else:
            offset = 0  # 重新开始

        # 确保不越界（循环）
        if offset >= len(all_scored):
            offset = 0

        # 4. 取6个（从 offset 开始）
        teachers = all_scored[offset:offset + 6]
        if len(teachers) < 6:
            # 如果不够6个，从头补（避免重复）
            remaining = 6 - len(teachers)
            for t in all_scored[:remaining]:
                if t not in teachers:
                    teachers.append(t)
            offset = 0

        # 保存新的 offset
        try:
            set_recommend_offset(session_id, offset)
        except Exception:
            pass  # 兼容旧数据库

        # 5. 构建显示列表
        teacher_list = []
        for idx, t in enumerate(teachers, 1):
            teacher_list.append(
                f"导师{idx}\n"
                f"姓名：{t['name']}\n"
                f"匹配度：{t['score']}\n"
                f"研究方向：{', '.join(t.get('research', []))}\n"
                f"课程：{', '.join(t.get('courses', []))}\n"
                f"邮箱：{t.get('email', '')}\n"
                f"主页：{t.get('homepage', '')}\n"
            )
        teacher_text = "\n".join(teacher_list)

        profile_summary = build_profile_brief(profile)

        # 6. 让 LLM 生成一段总体推荐说明
        prompt = f"""
        你是广州大学机械与电气工程学院的导师推荐专家。
        根据用户画像，请为以下候选导师写一段约150字的推荐说明，说明这些导师为什么适合该学生。
        不要单独列出导师，只进行总体分析。语言亲切、专业。

        用户画像摘要：
        {profile_summary}

        候选导师（供参考）：
        {teacher_text}

        请生成推荐说明：
        """
        analysis = llm.invoke(prompt).content

        # 7. 拼接最终回复，加上换一批提示
        final_reply = f"为你找到以下匹配导师：\n\n{teacher_text}\n\n推荐分析：{analysis}\n\n---\n不满意？可以告诉我「换一批」或继续点击推荐按钮，我会为你推荐其他导师。"
        messages = state.get("messages", []) + [
            HumanMessage(content=state["user_input"]),
            AIMessage(content=final_reply)
        ]
        return {
            "response": final_reply,
            "messages": messages
        }
    except Exception as e:
        # 兜底：如果推荐出错，返回友好提示
        logger.error("推荐导师出错: %s", str(e), exc_info=True)
        reply = "抱歉，推荐导师时遇到了一些问题。请稍后再试，或者先告诉我您的兴趣方向。"
        messages = state.get("messages", []) + [
            HumanMessage(content=state["user_input"]),
            AIMessage(content=reply)
        ]
        return {"response": reply, "messages": messages}


def build_welcome_prompt(profile):
    """根据画像状态生成引导性欢迎词"""
    interests = profile.get("interest", {})
    goals = profile.get("goal", {})
    history = profile.get("history", [])

    has_interests = len(interests) > 0
    has_goals = len(goals) > 0
    has_history = len(history) > 0

    # 构建兴趣列表供引导
    interest_names = [NAME_MAP.get(k, k) for k in INTEREST_MAP.keys()]
    goal_names = [NAME_MAP.get(k, k) for k in GOAL_MAP.keys()]

    if not has_interests and not has_goals:
        # 新用户，完全无画像
        prompt = f"""你是 Mario，广州大学机械与电气工程学院的导师推荐助手。你的名字来自超级马里奥，因为你像马里奥一样乐于助人、充满活力。
这是用户第一次与你对话，用户还没有任何画像信息。
请用一段活泼轻松的欢迎语（约80-120字）引导用户介绍自己，包括：
1. 自我介绍：你是 Mario，专门帮大家挑导师
2. 引导用户说说自己的兴趣方向（举2-3个例子即可，如机器人、人工智能、嵌入式）
3. 引导用户说说自己的未来目标（举1-2个例子即可，如就业、考研）
4. 告诉用户可以随时说"查看我的画像"或"推荐导师"
要求：语气活泼轻松，像朋友在聊天，不要用 emoji，不要用颜文字，不要用感叹号堆砌。不要罗列太多方向，保持简洁自然。"""
    elif has_interests and not has_goals:
        # 有兴趣但无目标
        interest_summary = "、".join([NAME_MAP.get(k, k) for k in interests.keys()])
        prompt = f"""你是 Mario，广州大学机械与电气工程学院的导师推荐助手。
用户已有兴趣方向：{interest_summary}，但还没有设定目标。
请用一段活泼轻松的话（约80-120字）：
1. 肯定用户已有的兴趣
2. 引导用户说说未来的目标（如：{", ".join(goal_names)}）
3. 告诉用户可以随时说"查看我的画像"或"推荐导师"
要求：语气活泼轻松，像朋友在聊天，不要用 emoji，不要用颜文字。"""
    elif not has_interests and has_goals:
        # 有目标但无兴趣
        goal_summary = "、".join([NAME_MAP.get(k, k) for k in goals.keys()])
        prompt = f"""你是 Mario，广州大学机械与电气工程学院的导师推荐助手。
用户已有目标：{goal_summary}，但还没有记录兴趣方向。
请用一段活泼轻松的话（约80-120字）：
1. 肯定用户已有的目标
2. 引导用户说说感兴趣的研究方向（如：{", ".join(interest_names)}）
3. 告诉用户可以随时说"查看我的画像"或"推荐导师"
要求：语气活泼轻松，像朋友在聊天，不要用 emoji，不要用颜文字。"""
    else:
        # 已有完整画像
        interest_summary = "、".join([NAME_MAP.get(k, k) for k in interests.keys()])
        goal_summary = "、".join([NAME_MAP.get(k, k) for k in goals.keys()])
        prompt = f"""你是 Mario，广州大学机械与电气工程学院的导师推荐助手。
用户已有画像信息：
- 兴趣方向：{interest_summary}
- 目标：{goal_summary}
请用一段活泼轻松的话（约60-100字）：
1. 简要回顾用户的画像
2. 询问是否需要推荐导师，或者继续更新画像
3. 告诉用户可以随时说"查看我的画像"或"推荐导师"
要求：语气活泼轻松，像朋友在聊天，不要用 emoji，不要用颜文字。"""
    return prompt


def welcome_node(state: State):
    """系统启动时的欢迎节点，生成引导性欢迎词"""
    session_id = state.get("session_id", "default")
    profile = load_profile(session_id)
    prompt = build_welcome_prompt(profile)
    response = llm.invoke(prompt)
    welcome_text = response.content

    # 将欢迎词作为第一条 AI 消息
    messages = [AIMessage(content=welcome_text)]

    return {
        "response": welcome_text,
        "messages": messages
    }


def explore_node(state: State):
    """当学生表示迷茫、想了解方向时，LLM 主动介绍各研究方向"""
    interest_names = [NAME_MAP.get(k, k) for k in INTEREST_MAP.keys()]
    goal_names = [NAME_MAP.get(k, k) for k in GOAL_MAP.keys()]

    prompt = f"""你是广州大学机械与电气工程学院的学长/学姐，热情、亲切。
用户表示迷茫，不知道自己喜欢什么方向，请你用一段话（约200-300字）：
1. 先安慰用户，告诉ta大一迷茫很正常
2. 简要介绍学院的主要研究方向，让用户有个大致了解：
   {', '.join(interest_names)}
3. 介绍可能的未来目标方向：
   {', '.join(goal_names)}
4. 鼓励用户说说哪个方向听起来有意思，或者聊聊平时的兴趣爱好
要求：语气亲切自然，像学长/学姐在聊天，不要像机器人一样生硬。"""
    response = llm.invoke(prompt)

    messages = state.get("messages", []) + [
        HumanMessage(content=state["user_input"]),
        AIMessage(content=response.content)
    ]
    return {
        "response": response.content,
        "messages": messages
    }


def reset_profile_node(state: State):
    """重置用户画像"""
    session_id = state.get("session_id", "default")
    # 清空画像
    empty_profile = {"interest": {}, "goal": {}, "history": []}
    save_profile(empty_profile, session_id)

    reply = "已为您清空所有画像信息，我们可以重新开始！请告诉我您的兴趣方向吧。"
    messages = state.get("messages", []) + [
        HumanMessage(content=state["user_input"]),
        AIMessage(content=reply)
    ]
    return {
        "response": reply,
        "messages": messages,
        "user_profile": empty_profile
    }


def load_teachers_data():
    """加载导师 JSON 数据，返回精简后的列表"""
    import json
    project_root = os.path.dirname(os.path.dirname(BASE_DIR))
    teachers_path = os.path.join(project_root, "app", "gzhu_teachers.json")
    if not os.path.exists(teachers_path):
        teachers_path = os.path.join(project_root, "gzhu_teachers.json")
    try:
        with open(teachers_path, "r", encoding="utf-8") as f:
            teachers = json.load(f)
        # 精简：只保留姓名、研究方向、课程（不暴露邮箱主页等隐私）
        simplified = []
        for t in teachers:
            simplified.append({
                "name": t.get("name", ""),
                "research": t.get("research", []),
                "courses": t.get("courses", [])
            })
        return simplified
    except Exception as e:
        print("加载导师数据失败:", e)
        return []


def chat_node(state: State):
    """聊天节点，注入全部导师信息，支持查询各类导师问题"""
    session_id = state.get("session_id", "default")
    profile = load_profile(session_id)

    # 构建全部导师信息摘要（不再限制前10个）
    teacher_summary = ""
    for t in ALL_TEACHERS:
        research = "、".join(t.get("research", [])) or "暂无"
        courses = "、".join(t.get("courses", [])) or "暂无"
        teacher_summary += f"- {t['name']}：研究方向【{research}】，课程【{courses}】\n"

    # 构建用户画像摘要
    interests = get_sorted_profile(profile.get("interest", {}))
    goals = get_sorted_profile(profile.get("goal", {}))
    interest_text = "、".join([f"{NAME_MAP.get(n, n)}({d['composite_score']})" for n, d in interests[:3]]) or "暂无"
    goal_text = "、".join([f"{NAME_MAP.get(n, n)}({d['composite_score']})" for n, d in goals[:3]]) or "暂无"

    system_prompt = f"""你是 Mario，广州大学机械与电气工程学院的导师推荐助手。你的名字来自超级马里奥，因为你像马里奥一样乐于助人、充满活力。
你可以回答关于学院导师的任何问题，包括介绍导师的研究方向、课程等。

当前用户的画像信息：
- 兴趣方向：{interest_text}
- 目标：{goal_text}

以下是学院的全部导师信息（供你参考回答导师相关问题）：
{teacher_summary}

注意：
1. 如果用户问"XXX老师怎么样"、"介绍一下XXX老师"，请根据导师信息回答
2. 如果用户问"XX专业/方向有几位导师"、"XX方向的硕士导师"、"XX课程的老师"，请根据导师信息列出符合条件的导师
3. 如果用户问"网络安全方面的导师"、"机器人的导师"等方向性问题，请根据研究方向匹配并列出相关导师
4. 如果用户问的导师不在列表中，如实说"暂未找到该导师的信息"
5. 如果用户问与导师无关的问题，正常闲聊即可
6. 回答要亲切自然，像朋友在聊天"""

    # 将 system prompt 作为第一条 system 消息
    messages = state.get("messages", [])
    chat_messages = [HumanMessage(content=system_prompt), HumanMessage(content=state["user_input"])]
    response = llm.invoke(chat_messages)
    messages.append(HumanMessage(content=state["user_input"]))
    messages.append(AIMessage(content=response.content))

    return {
        "response": response.content,
        "messages": messages
    }


def router(state):
    return state["intent"]


def build_graph():
    builder = StateGraph(State)
    builder.add_node("intent", intent_node)
    builder.add_node("profile", profile_node)
    builder.add_node("confirm_profile", confirm_profile_node)
    builder.add_node("show_profile", show_profile_summary_node)
    builder.add_node("recommend", recommend_node)
    builder.add_node("explore", explore_node)
    builder.add_node("reset_profile", reset_profile_node)
    builder.add_node("chat", chat_node)

    builder.set_entry_point("intent")
    builder.add_conditional_edges("intent", router,
                                  {"show_profile": "show_profile",
                                   "update_profile": "profile",
                                   "recommend": "recommend",
                                   "explore": "explore",
                                   "reset_profile": "reset_profile",
                                   "chat": "chat"})
    builder.add_edge("profile", "confirm_profile")
    builder.add_edge("confirm_profile", END)
    builder.add_edge("recommend", END)
    builder.add_edge("chat", END)
    builder.add_edge("show_profile", END)
    builder.add_edge("explore", END)
    builder.add_edge("reset_profile", END)

    return builder.compile()


graph = build_graph()


def run_agent(user_input, messages=None, session_id="default"):
    if messages is None:
        messages = []

    result = graph.invoke({
        "messages": messages,
        "user_input": user_input,
        "intent": "",
        "user_profile": load_profile(session_id),
        "analysis_result": {},
        "approval": False,
        "response": "",
        "next_step": "",
        "session_id": session_id
    })

    # 获取最新的画像（优先使用 result 中更新过的，否则从数据库读取）
    profile = load_profile(session_id)

    # 将本次对话记录到数据库（无论什么 intent 都记录）
    # 检查是否已经记录过这条消息（避免重复记录）
    already_recorded = db_check_recent_history(session_id, user_input)
    if not already_recorded:
        db_add_history(
            session_id=session_id,
            message=user_input,
            intent=result.get("intent", "chat"),
            response=result.get("response", ""),
            update_data=result.get("analysis_result", {})
        )

    # 如果画像有更新（profile 节点执行过），保存到数据库
    if result.get("intent") == "update_profile":
        save_profile(result.get("user_profile", profile), session_id)

    return result["response"], result.get("messages", messages)


def get_welcome_message(session_id="default"):
    """生成系统启动时的欢迎引导消息"""
    profile = load_profile(session_id)
    prompt = build_welcome_prompt(profile)
    response = llm.invoke(prompt)
    return response.content


if __name__ == "__main__":
    print("=" * 60)
    print("  广州大学机械与电气工程学院 — 智能导师推荐系统")
    print("=" * 60)
    print()
    messages = []
    # 生成欢迎引导消息
    welcome = get_welcome_message()
    print(f"🤖 {welcome}")
    print()
    messages = [AIMessage(content=welcome)]

    while True:
        user_input = input("👤 请说（输入 exit 退出）：")
        if user_input.lower() in ["exit", "quit"]:
            print("👋 再见！")
            break
        response, messages = run_agent(user_input, messages)
        print(f"\n🤖 {response}\n")