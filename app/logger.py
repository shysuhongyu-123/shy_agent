"""
日志模块 — 替代 print()，支持文件日志和控制台输出

用法：
    from app.logger import logger
    logger.info("用户登录成功")
    logger.error("推荐导师失败: %s", str(e))
"""

import logging
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "..", "logs")

# 确保日志目录存在
os.makedirs(LOG_DIR, exist_ok=True)

# ============================================================
# 日志配置
# ============================================================

# 日志格式：时间 - 级别 - 模块 - 消息
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 创建 logger
logger = logging.getLogger("gzhu_agent")
logger.setLevel(logging.DEBUG)

# 防止重复添加 handler
if not logger.handlers:
    # 1. 控制台 handler（输出到 stderr，PythonAnywhere 会捕获到 Error log）
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(console_handler)

    # 2. 文件 handler（按天分割）
    today = datetime.now().strftime("%Y-%m-%d")
    file_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"app_{today}.log"),
        encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(file_handler)

    # 3. 错误日志文件（只记录 ERROR 及以上）
    error_handler = logging.FileHandler(
        os.path.join(LOG_DIR, f"error_{today}.log"),
        encoding="utf-8"
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    logger.addHandler(error_handler)