import sqlite3
from typing import List, Dict, Optional
from datetime import datetime, timedelta

DB_NAME = "clinic.db"

def save_turn(
    user_phone: Optional[str],
    role: str,
    message: str,
    intent: Optional[str] = None,
    tool_name: Optional[str] = None,
    result: Optional[str] = None,
) -> None:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO conversation_memory (user_phone, role, message, intent, tool_name, result)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_phone or "anonymous", role, message, intent, tool_name, result))
        conn.commit()

def load_recent(user_phone: Optional[str], k: int = 10) -> List[Dict]:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT role, message, created_at, intent, tool_name, result
            FROM conversation_memory
            WHERE user_phone = ?
            ORDER BY id ASC
            LIMIT ?
        """, (user_phone or "anonymous", k))
        rows = cur.fetchall()
    return [
        {
            "role": r,
            "message": m,
            "created_at": t,
            "intent": i,
            "tool_name": tool,
            "result": res,
        }
        for (r, m, t, i, tool, res) in rows
    ]

def cleanup_old_conversations(days: int = 7) -> None:
    cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            DELETE FROM conversation_memory
            WHERE created_at < ?
        """, (cutoff,))
        conn.commit()
