"""
SQLite 数据库模块 — 替代 JSON 文件存储用户画像

支持多用户隔离存储，每个用户（由 session_id 标识）拥有独立的画像数据。
"""

import sqlite3
import os
import json
from datetime import datetime
from typing import Optional, Dict, List

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "profiles.db")


def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # 提高并发性能
    return conn


def init_db():
    """初始化数据库表结构"""
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                session_id TEXT PRIMARY KEY,
                interest TEXT NOT NULL DEFAULT '{}',
                goal TEXT NOT NULL DEFAULT '{}',
                recommend_offset INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
            );

            CREATE TABLE IF NOT EXISTS profile_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                time TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
                message TEXT NOT NULL,
                intent TEXT DEFAULT '',
                response TEXT DEFAULT '',
                update_data TEXT DEFAULT '{}',
                FOREIGN KEY (session_id) REFERENCES profiles(session_id)
            );

            CREATE INDEX IF NOT EXISTS idx_history_session
                ON profile_history(session_id, time);
        """)
        conn.commit()
    finally:
        conn.close()


def load_profile(session_id: str) -> dict:
    """
    从数据库加载指定用户的画像。
    如果用户不存在，返回默认空画像。
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT interest, goal FROM profiles WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "interest": json.loads(row["interest"]),
                "goal": json.loads(row["goal"]),
                "history": load_history(session_id)
            }
        else:
            return {
                "interest": {},
                "goal": {},
                "history": []
            }
    finally:
        conn.close()


def save_profile(session_id: str, profile: dict):
    """
    保存或更新指定用户的画像（interest 和 goal 部分）。
    history 通过 add_history 单独添加。
    """
    conn = get_connection()
    try:
        interest_json = json.dumps(profile.get("interest", {}), ensure_ascii=False)
        goal_json = json.dumps(profile.get("goal", {}), ensure_ascii=False)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn.execute("""
            INSERT INTO profiles (session_id, interest, goal, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(session_id) DO UPDATE SET
                interest = excluded.interest,
                goal = excluded.goal,
                updated_at = excluded.updated_at
        """, (session_id, interest_json, goal_json, now, now))
        conn.commit()
    finally:
        conn.close()


def load_history(session_id: str, limit: int = 100) -> list:
    """加载指定用户的历史记录"""
    conn = get_connection()
    try:
        cursor = conn.execute("""
            SELECT time, message, intent, response, update_data
            FROM profile_history
            WHERE session_id = ?
            ORDER BY time DESC
            LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()
        history = []
        for row in reversed(rows):  # 反转回正序
            history.append({
                "time": row["time"],
                "message": row["message"],
                "intent": row["intent"],
                "response": row["response"],
                "update": json.loads(row["update_data"])
            })
        return history
    finally:
        conn.close()


def add_history(session_id: str, message: str, intent: str = "",
                response: str = "", update_data: dict = None):
    """添加一条历史记录"""
    if update_data is None:
        update_data = {}
    conn = get_connection()
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        update_json = json.dumps(update_data, ensure_ascii=False)
        conn.execute("""
            INSERT INTO profile_history (session_id, time, message, intent, response, update_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session_id, now, message, intent, response, update_json))
        conn.commit()
    finally:
        conn.close()


def check_recent_history(session_id: str, message: str) -> bool:
    """
    检查最近是否有相同的消息记录（避免重复记录）。
    返回 True 表示已存在。
    """
    conn = get_connection()
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        cursor = conn.execute("""
            SELECT COUNT(*) as cnt FROM profile_history
            WHERE session_id = ? AND message = ? AND time LIKE ?
        """, (session_id, message, f"{today}%"))
        row = cursor.fetchone()
        return row["cnt"] > 0
    finally:
        conn.close()


def delete_profile(session_id: str):
    """删除指定用户的所有数据"""
    conn = get_connection()
    try:
        conn.execute("DELETE FROM profile_history WHERE session_id = ?", (session_id,))
        conn.execute("DELETE FROM profiles WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        conn.close()


# ============================================================
# 推荐偏移量管理（用于"换一批"功能）
# ============================================================

def get_recommend_offset(session_id: str) -> int:
    """获取当前用户的推荐偏移量"""
    conn = get_connection()
    try:
        # 先检查列是否存在（兼容旧数据库）
        cursor = conn.execute("PRAGMA table_info(profiles)")
        columns = [row["name"] for row in cursor.fetchall()]
        if "recommend_offset" not in columns:
            return 0
        cursor = conn.execute(
            "SELECT recommend_offset FROM profiles WHERE session_id = ?",
            (session_id,)
        )
        row = cursor.fetchone()
        if row and row["recommend_offset"] is not None:
            return int(row["recommend_offset"])
        return 0
    finally:
        conn.close()


def set_recommend_offset(session_id: str, offset: int):
    """设置当前用户的推荐偏移量"""
    conn = get_connection()
    try:
        conn.execute("""
            UPDATE profiles SET recommend_offset = ? WHERE session_id = ?
        """, (offset, session_id))
        conn.commit()
    finally:
        conn.close()


# 应用启动时初始化数据库
init_db()
