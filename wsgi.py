"""
WSGI 入口文件 — 用于生产部署（gunicorn / PythonAnywhere）

用法：
    gunicorn wsgi:application

或直接在 PythonAnywhere 的 Web 面板中设置：
    Source code: /home/yourusername/gzhu_agent_web
    Working directory: /home/yourusername/gzhu_agent_web
    WSGI config: /var/www/yourusername_pythonanywhere_com_wsgi.py
                   (内容指向此文件)
"""
import sys
import os

# 添加项目路径到 Python 路径
path = os.path.dirname(os.path.abspath(__file__))
if path not in sys.path:
    sys.path.insert(0, path)

# 加载 .env 文件（如果存在）
env_path = os.path.join(path, ".env")
if os.path.exists(env_path):
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        # 手动加载 .env
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip()
                    if key not in os.environ:
                        os.environ[key] = value

# 导入 Flask 应用实例
from run import app as application