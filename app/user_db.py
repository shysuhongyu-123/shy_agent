"""
用户认证数据库模块 — 支持注册、登录、会话管理

使用 SQLite 存储用户信息，密码使用 SHA-256 + salt 哈希存储。
使用 threading.Lock 保证写入操作的线程安全。
"""
import sqlite3
import os
import hashlib
import secrets
import threading
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "users.db")

# 写锁：所有写入操作必须获取此锁
_write_lock = threading.Lock()


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """初始化用户表"""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                last_login TEXT
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_token ON sessions(token);
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
        """)
        conn.commit()
    finally:
        conn.close()


def hash_password(password: str) -> str:
    """使用 SHA-256 + salt 哈希密码"""
    salt = secrets.token_hex(16)
    h = hashlib.sha256((salt + password).encode()).hexdigest()
    return f"{salt}${h}"


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码"""
    try:
        salt, h = password_hash.split("$")
        return hashlib.sha256((salt + password).encode()).hexdigest() == h
    except Exception:
        return False


def register_user(username: str, password: str) -> dict:
    """
    注册新用户。
    返回: {"success": True/False, "message": "..."}
    使用写锁保证线程安全。
    """
    if len(username) < 2 or len(username) > 20:
        return {"success": False, "message": "用户名长度应为2-20个字符"}
    if len(password) < 6:
        return {"success": False, "message": "密码长度至少6位"}

    with _write_lock:
        conn = get_connection()
        try:
            # 检查用户名是否已存在
            cursor = conn.execute("SELECT id FROM users WHERE username = ?", (username,))
            if cursor.fetchone():
                return {"success": False, "message": "用户名已存在"}

            # 创建用户
            password_hash = hash_password(password)
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO users (username, password_hash, created_at) VALUES (?, ?, ?)",
                (username, password_hash, now)
            )
            conn.commit()
            return {"success": True, "message": "注册成功"}
        except Exception as e:
            return {"success": False, "message": f"注册失败: {str(e)}"}
        finally:
            conn.close()


def login_user(username: str, password: str) -> dict:
    """
    用户登录，生成会话 token。
    返回: {"success": True/False, "message": "...", "token": "...", "username": "..."}
    使用写锁保证线程安全。
    """
    with _write_lock:
        conn = get_connection()
        try:
            cursor = conn.execute(
                "SELECT id, password_hash FROM users WHERE username = ?",
                (username,)
            )
            row = cursor.fetchone()
            if not row:
                return {"success": False, "message": "用户名或密码错误"}

            if not verify_password(password, row["password_hash"]):
                return {"success": False, "message": "用户名或密码错误"}

            # 生成会话 token（有效期7天）
            token = secrets.token_hex(32)
            now = datetime.now()
            expires = now + timedelta(days=7)
            now_str = now.strftime("%Y-%m-%d %H:%M:%S")
            expires_str = expires.strftime("%Y-%m-%d %H:%M:%S")

            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, row["id"], now_str, expires_str)
            )
            # 更新最后登录时间
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (now_str, row["id"])
            )
            conn.commit()

            return {
                "success": True,
                "message": "登录成功",
                "token": token,
                "username": username
            }
        except Exception as e:
            return {"success": False, "message": f"登录失败: {str(e)}"}
        finally:
            conn.close()


def validate_token(token: str) -> dict:
    """
    验证会话 token 是否有效。
    返回: {"valid": True/False, "user_id": ..., "username": "..."}
    """
    if not token:
        return {"valid": False}

    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT s.user_id, u.username
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.token = ? AND s.expires_at > datetime('now', 'localtime')
        """, (token,))
        row = cursor.fetchone()
        if row:
            return {
                "valid": True,
                "user_id": row["user_id"],
                "username": row["username"]
            }
        return {"valid": False}
    except Exception:
        return {"valid": False}
    finally:
        conn.close()


def logout_user(token: str):
    """登出，删除会话 token，使用写锁保证线程安全"""
    with _write_lock:
        conn = get_connection()
        try:
            conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
            conn.commit()
        finally:
            conn.close()


# 应用启动时初始化数据库
init_db()