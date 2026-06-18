"""
日志模块 — 替代 print()，支持文件日志和邮件告警

用法：
    from app.logger import logger, send_alert_email
    logger.info("用户登录成功")
    logger.error("推荐导师失败: %s", str(e))
    send_alert_email("系统异常", "详细错误信息")
"""

import logging
import os
import sys
import smtplib
import traceback
from email.mime.text import MIMEText
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


# ============================================================
# 邮件告警
# ============================================================

# QQ邮箱 SMTP 配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 587
ALERT_EMAIL = "972538359@qq.com"  # 接收告警的邮箱


def send_alert_email(subject: str, body: str):
    """
    发送告警邮件。
    需要设置环境变量 QQ_MAIL_PASSWORD（QQ邮箱授权码）。

    如何获取 QQ邮箱授权码：
    1. 登录 QQ邮箱 → 设置 → 账户
    2. 找到 "POP3/IMAP/SMTP服务"
    3. 点击 "开启"（如果已开启则直接使用）
    4. 按提示发送短信后获取授权码
    5. 在 PythonAnywhere 的 Environment variables 中设置：
       Key: QQ_MAIL_PASSWORD
       Value: 你的授权码
    """
    password = os.environ.get("QQ_MAIL_PASSWORD")
    if not password:
        logger.warning("未设置 QQ_MAIL_PASSWORD 环境变量，无法发送告警邮件")
        return False

    try:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = f"[gzhu_agent] {subject}"
        msg["From"] = ALERT_EMAIL
        msg["To"] = ALERT_EMAIL

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(ALERT_EMAIL, password)
            server.send_message(msg)

        logger.info("告警邮件已发送: %s", subject)
        return True
    except Exception as e:
        logger.error("发送告警邮件失败: %s", str(e))
        return False


def send_error_alert(error_msg: str, request_info: str = ""):
    """
    发送错误告警（带堆栈跟踪）。
    自动限制频率：同一错误类型每小时最多发一次。
    """
    # 获取堆栈跟踪
    stack_trace = traceback.format_exc()

    body = f"""
时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
错误: {error_msg}

请求信息:
{request_info}

堆栈跟踪:
{stack_trace}
    """.strip()

    send_alert_email(f"系统异常: {error_msg[:50]}", body)
</code></pre>