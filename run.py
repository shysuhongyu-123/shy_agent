import sys
import os

# 确保能找到 app 模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 加载 .env 文件中的环境变量（必须在导入其他模块之前执行）
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 跳过空行和注释
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip()
                # 只设置尚未被系统环境变量覆盖的变量
                if key not in os.environ:
                    os.environ[key] = value

from flask import Flask, request, jsonify, render_template, redirect
from app.agent.trying import run_agent, get_welcome_message
from app.user_db import register_user, login_user, validate_token, logout_user

# 指定模板和静态文件夹路径
base_dir = os.path.dirname(os.path.abspath(__file__))
template_dir = os.path.join(base_dir, "app", "templates")
static_dir = os.path.join(base_dir, "app", "static")
app = Flask(__name__, template_folder=template_dir, static_folder=static_dir, static_url_path="/static")

# 全局会话消息存储（短期记忆，长期画像存储在 SQLite）
sessions = {}


def get_session_id():
    """
    从请求中获取用户标识。
    优先使用 token 对应的 username，否则用 IP 地址。
    """
    data = request.get_json(silent=True) or {}
    token = data.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        result = validate_token(token)
        if result["valid"]:
            return f"user_{result['username']}"
    # 兼容旧版：前端传来的 session_id
    session_id = data.get("session_id")
    if session_id:
        return session_id
    return request.remote_addr or "default"


# ============================================================
# 认证相关路由
# ============================================================

@app.route("/login")
def login_page():
    """登录页面"""
    return render_template("login.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    """注册 API"""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    result = register_user(username, password)
    return jsonify(result)


@app.route("/api/login", methods=["POST"])
def api_login():
    """登录 API"""
    data = request.get_json()
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()
    result = login_user(username, password)
    return jsonify(result)


@app.route("/api/verify", methods=["POST"])
def api_verify():
    """验证 token 是否有效"""
    data = request.get_json()
    token = data.get("token", "")
    result = validate_token(token)
    return jsonify(result)


@app.route("/api/logout", methods=["POST"])
def api_logout():
    """登出 API"""
    data = request.get_json()
    token = data.get("token", "")
    logout_user(token)
    return jsonify({"success": True})


# ============================================================
# 聊天相关路由
# ============================================================

@app.route("/")
def index():
    """主页面（聊天界面），未登录则跳转到登录页"""
    # 检查是否已登录（通过 query 参数或 header）
    token = request.args.get("token") or request.headers.get("Authorization", "").replace("Bearer ", "")
    if token:
        result = validate_token(token)
        if result["valid"]:
            return render_template("index.html", username=result["username"])
    # 前端会通过 localStorage 中的 token 来判断是否已登录
    return render_template("index.html", username="")


@app.route("/welcome", methods=["POST"])
def welcome():
    """返回个性化欢迎引导消息"""
    session_id = get_session_id()
    welcome_text = get_welcome_message(session_id)
    # 为每个新会话初始化消息列表
    sessions[session_id] = [{"role": "assistant", "content": welcome_text}]
    return jsonify({"reply": welcome_text})


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    user_input = data.get("message", "").strip()
    if not user_input:
        return jsonify({"reply": "请输入内容"})

    session_id = get_session_id()
    # 获取该会话的历史消息（转换为 LangChain 消息格式）
    history = sessions.get(session_id, [])
    from langchain_core.messages import HumanMessage, AIMessage

    messages = []
    for msg in history:
        if msg["role"] == "user":
            messages.append(HumanMessage(content=msg["content"]))
        elif msg["role"] == "assistant":
            messages.append(AIMessage(content=msg["content"]))

    # 调用 agent（传入 session_id 以支持多用户隔离）
    response, updated_messages = run_agent(user_input, messages, session_id=session_id)

    # 更新会话历史
    history.append({"role": "user", "content": user_input})
    history.append({"role": "assistant", "content": response})
    sessions[session_id] = history

    return jsonify({"reply": response})


if __name__ == "__main__":
    print("=" * 60)
    print("  广州大学机械与电气工程学院 — 智能导师推荐系统")
    print("  Web 界面: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, host="0.0.0.0", port=5000)