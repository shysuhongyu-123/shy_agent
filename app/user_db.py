"""
用户认证数据库模块 — 支持学号+姓名登录（无密码）

使用 SQLite 存储用户信息，学号作为唯一标识。
使用 threading.Lock 保证写入操作的线程安全。
"""
import sqlite3
import os
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
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
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


def register_or_login(student_id: str, name: str) -> dict:
    """
    学号+姓名登录/注册。
    如果学号已存在且姓名匹配，直接登录。
    如果学号已存在但姓名不匹配，返回错误。
    如果学号不存在，自动注册。

    返回: {"success": True/False, "message": "...", "token": "...", "username": "..."}
    """
    if not student_id or not name:
        return {"success": False, "message": "请填写学号和姓名"}

    with _write_lock:
        conn = get_connection()
        try:
            # 检查学号是否已存在
            cursor = conn.execute(
                "SELECT id, name FROM users WHERE student_id = ?",
                (student_id,)
            )
            row = cursor.fetchone()

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if row:
                # 学号已存在，验证姓名
                if row["name"] != name:
                    return {"success": False, "message": "学号和姓名不匹配，请检查后重试"}

                user_id = row["id"]
                is_new = False
            else:
                # 学号不存在，自动注册
                conn.execute(
                    "INSERT INTO users (student_id, name, created_at) VALUES (?, ?, ?)",
                    (student_id, name, now)
                )
                conn.commit()
                cursor = conn.execute(
                    "SELECT id FROM users WHERE student_id = ?",
                    (student_id,)
                )
                user_id = cursor.fetchone()["id"]
                is_new = True

            # 生成会话 token（有效期7天）
            token = secrets.token_hex(32)
            expires = datetime.now() + timedelta(days=7)
            expires_str = expires.strftime("%Y-%m-%d %H:%M:%S")

            conn.execute(
                "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
                (token, user_id, now, expires_str)
            )
            # 更新最后登录时间
            conn.execute(
                "UPDATE users SET last_login = ? WHERE id = ?",
                (now, user_id)
            )
            conn.commit()

            msg = "登录成功" if not is_new else "注册成功"
            return {
                "success": True,
                "message": msg,
                "token": token,
                "username": name,
                "student_id": student_id
            }
        except Exception as e:
            return {"success": False, "message": f"操作失败: {str(e)}"}
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
            SELECT s.user_id, u.name as username
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