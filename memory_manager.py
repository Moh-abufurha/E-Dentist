import sqlite3
from typing import List,Dict,Optional


DB_NAME="clinic.db"

def save_turn(user_phone: Optional[str],role:str,message:str)->None:
    with sqlite3.connect(DB_NAME) as conn:
        cur=conn.cursor()
        cur.execute("""
            INSERT INTO conversation_memory (user_phone, role, message)
            VALUES (?, ?, ?)
        """, (user_phone or "anonymous", role, message))
        conn.commit()


def load_recent(user_phone: Optional[str], k: int = 10) -> List[Dict]:
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT role, message, created_at
            FROM conversation_memory
            WHERE user_phone = ?
            ORDER BY id DESC
            LIMIT ?
        """, (user_phone or "anonymous", k))
        rows = cur.fetchall()
    # أحدث -> أقدم؟ قلب الترتيب للعرض
    return [{"role": r, "message": m, "created_at": t} for (r, m, t) in rows[::-1]]
