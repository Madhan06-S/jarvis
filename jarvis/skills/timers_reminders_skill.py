"""
JARVIS Timers & Reminders Skill (Persisted in SQLite)
"""
import re
import sqlite3
import time
from typing import Dict, Any

NAME = "Timers & Reminders"
DESCRIPTION = "Set timers, alarms, and reminders (persisted in SQLite)"
TRIGGERS = ["timer", "alarm", "reminder", "remind me", "list reminders"]

def _init_db():
    conn = sqlite3.connect("data/reminders.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            trigger_timestamp REAL,
            created_at REAL,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.commit()
    conn.close()

_init_db()

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()
    
    # List reminders
    if "list" in t or "show" in t or "my reminders" in t:
        conn = sqlite3.connect("data/reminders.db")
        c = conn.cursor()
        c.execute("SELECT title, trigger_timestamp FROM reminders WHERE status='pending' ORDER BY trigger_timestamp ASC")
        rows = c.fetchall()
        conn.close()
        
        if not rows:
            return {
                "handled": True,
                "spoken_response": "You have no active timers or reminders.",
                "hud_card": {"type": "reminders", "title": "REMINDERS", "data": []}
            }
            
        reminders_list = []
        for r in rows:
            reminders_list.append({"title": r[0], "time": time.strftime("%H:%M:%S", time.localtime(r[1]))})
            
        return {
            "handled": True,
            "spoken_response": f"You have {len(rows)} active reminders.",
            "hud_card": {"type": "reminders", "title": "ACTIVE REMINDERS", "data": reminders_list}
        }

    # Set timer / reminder
    tm_match = re.search(r"(?:set\s+)?(?:timer|reminder|alarm)\s+(?:for\s+)?(\d+)\s*(min|minute|sec|second|hour)", t)
    title = "Timer"
    rem_match = re.search(r"remind me to\s+(.+)", t)
    if rem_match:
        title = rem_match.group(1).strip()

    num, unit = 5, "min"
    if tm_match:
        num = int(tm_match.group(1))
        unit = tm_match.group(2)
        
    duration_sec = num * 60 if "min" in unit else (num * 3600 if "hour" in unit else num)
    trigger_ts = time.time() + duration_sec
    
    conn = sqlite3.connect("data/reminders.db")
    c = conn.cursor()
    c.execute("INSERT INTO reminders (title, trigger_timestamp, created_at) VALUES (?, ?, ?)", (title, trigger_ts, time.time()))
    conn.commit()
    conn.close()

    spoken = f"Timer set for {num} {unit}{'s' if num > 1 else ''} for '{title}'."
    return {
        "handled": True,
        "spoken_response": spoken,
        "action": {"action": "TIMER", "target": str(duration_sec)},
        "hud_card": {
            "type": "reminders",
            "title": "TIMER SET",
            "data": [{"title": title, "duration": f"{num} {unit}"}]
        }
    }
