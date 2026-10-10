"""
JARVIS Notes & To-Do List Skill
"""
import re
import sqlite3
import time
from typing import Dict, Any

NAME = "Notes & To-Do"
DESCRIPTION = "Manage quick notes and to-do list items (add to todo, what's on my todo)"
TRIGGERS = ["todo", "to-do", "add to my todo", "what's on my todo", "add note", "notes", "my notes"]

def _init_db():
    conn = sqlite3.connect("data/todos.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task TEXT,
            status TEXT DEFAULT 'pending',
            created_at REAL
        )
    """)
    conn.commit()
    conn.close()

_init_db()

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()

    # View items
    if any(q in t for q in ["what's on my todo", "view todo", "show todo", "my todo", "list todo", "my notes"]):
        conn = sqlite3.connect("data/todos.db")
        c = conn.cursor()
        c.execute("SELECT task FROM todos WHERE status='pending' ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        tasks = [r[0] for r in rows]
        if not tasks:
            return {
                "handled": True,
                "spoken_response": "Your to-do list is currently empty, sir.",
                "hud_card": {"type": "todo", "title": "TO-DO LIST", "data": []}
            }

        spoken = f"You have {len(tasks)} items on your to-do list: " + ", ".join(tasks[:3])
        return {
            "handled": True,
            "spoken_response": spoken,
            "hud_card": {"type": "todo", "title": "TO-DO LIST", "data": tasks}
        }

    # Add item
    m_add = re.search(r"(?:add\s+(?:to\s+my\s+todo|note|task)?\s*:?\s*)(.+)", t)
    item_text = m_add.group(1).strip() if m_add else query

    conn = sqlite3.connect("data/todos.db")
    c = conn.cursor()
    c.execute("INSERT INTO todos (task, created_at) VALUES (?, ?)", (item_text, time.time()))
    conn.commit()
    conn.close()

    return {
        "handled": True,
        "spoken_response": f"Added '{item_text}' to your to-do list.",
        "hud_card": {
            "type": "todo",
            "title": "TO-DO LIST",
            "data": [item_text]
        }
    }
