import sqlite3
import time
import json
import asyncio
from typing import List, Dict, Optional

DB_PATH = 'data/jarvis.db'

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA journal_mode=WAL')
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT DEFAULT '',
            importance INTEGER DEFAULT 5,
            created_at REAL NOT NULL,
            last_accessed REAL,
            access_count INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT DEFAULT '',
            priority TEXT DEFAULT 'medium',
            status TEXT DEFAULT 'open',
            due_date TEXT,
            due_time TEXT,
            project TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            notes TEXT DEFAULT '',
            created_at REAL NOT NULL,
            completed_at REAL
        );

        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT DEFAULT '',
            content TEXT NOT NULL,
            topic TEXT DEFAULT '',
            tags TEXT DEFAULT '[]',
            created_at REAL NOT NULL,
            updated_at REAL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts USING fts5(content, type, source, content='memories', content_rowid='id');
        CREATE VIRTUAL TABLE IF NOT EXISTS task_fts USING fts5(title, description, project, notes, content='tasks', content_rowid='id');
        CREATE VIRTUAL TABLE IF NOT EXISTS note_fts USING fts5(title, content, topic, content='notes', content_rowid='id');
    ''')
    conn.commit()
    conn.close()

def remember(content: str, mem_type: str = "fact", source: str = "", importance: int = 5) -> int:
    conn = get_connection()
    c = conn.cursor()
    now = time.time()
    c.execute(
        "INSERT INTO memories (type, content, source, importance, created_at, last_accessed) VALUES (?, ?, ?, ?, ?, ?)",
        (mem_type, content, source, importance, now, now)
    )
    mem_id = c.lastrowid
    c.execute("INSERT INTO memory_fts (rowid, content, type, source) VALUES (?, ?, ?, ?)", (mem_id, content, mem_type, source))
    conn.commit()
    conn.close()
    return mem_id

def sanitize_query(query: str) -> str:
    query = query.replace("'", "")
    words = [w for w in query.split() if len(w) > 2]
    return " OR ".join(words[:5])

def recall(query: str, limit: int = 5) -> List[Dict]:
    sanitized = sanitize_query(query)
    if not sanitized:
        return []
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT m.* FROM memory_fts f
            JOIN memories m ON f.rowid = m.id
            WHERE memory_fts MATCH ?
            ORDER BY m.importance DESC, m.last_accessed DESC
            LIMIT ?
        """, (sanitized, limit))
        results = [dict(row) for row in c.fetchall()]
        
        # update last accessed
        now = time.time()
        for r in results:
            c.execute("UPDATE memories SET last_accessed = ?, access_count = access_count + 1 WHERE id = ?", (now, r['id']))
        conn.commit()
    except sqlite3.OperationalError:
        results = []
    conn.close()
    return results

def get_recent_memories(limit: int = 10) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM memories ORDER BY created_at DESC LIMIT ?", (limit,))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_important_memories(limit: int = 10) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM memories ORDER BY importance DESC, last_accessed DESC LIMIT ?", (limit,))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def create_task(title: str, description: str = '', priority: str = 'medium', 
                due_date: str = '', due_time: str = '', project: str = '', tags: str = '[]') -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks (title, description, priority, due_date, due_time, project, tags, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (title, description, priority, due_date, due_time, project, tags, time.time()))
    task_id = c.lastrowid
    c.execute("INSERT INTO task_fts (rowid, title, description, project, notes) VALUES (?, ?, ?, ?, ?)", 
              (task_id, title, description, project, ''))
    conn.commit()
    conn.close()
    return task_id

def get_open_tasks(project: Optional[str] = None) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    query = "SELECT * FROM tasks WHERE status = 'open'"
    params = []
    if project:
        query += " AND project = ?"
        params.append(project)
    query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, due_date"
    c.execute(query, params)
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def get_tasks_for_date(date_str: str) -> List[Dict]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM tasks WHERE status = 'open' AND due_date = ?", (date_str,))
    results = [dict(row) for row in c.fetchall()]
    conn.close()
    return results

def complete_task(task_id: int):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'done', completed_at = ? WHERE id = ?", (time.time(), task_id))
    conn.commit()
    conn.close()

def search_tasks(query: str, limit: int = 5) -> List[Dict]:
    sanitized = sanitize_query(query)
    if not sanitized:
        return []
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT t.* FROM task_fts f
            JOIN tasks t ON f.rowid = t.id
            WHERE task_fts MATCH ?
            LIMIT ?
        """, (sanitized, limit))
        results = [dict(row) for row in c.fetchall()]
    except sqlite3.OperationalError:
        results = []
    conn.close()
    return results

def create_note(content: str, title: str = '', topic: str = '', tags: str = '[]') -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO notes (title, content, topic, tags, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (title, content, topic, tags, time.time(), time.time()))
    note_id = c.lastrowid
    c.execute("INSERT INTO note_fts (rowid, title, content, topic) VALUES (?, ?, ?, ?)", (note_id, title, content, topic))
    conn.commit()
    conn.close()
    return note_id

def search_notes(query: str, limit: int = 5) -> List[Dict]:
    sanitized = sanitize_query(query)
    if not sanitized:
        return []
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT n.* FROM note_fts f
            JOIN notes n ON f.rowid = n.id
            WHERE note_fts MATCH ?
            LIMIT ?
        """, (sanitized, limit))
        results = [dict(row) for row in c.fetchall()]
    except sqlite3.OperationalError:
        results = []
    conn.close()
    return results

def build_memory_context(user_message: str) -> str:
    tasks = get_open_tasks()
    high_priority = [t for t in tasks if t['priority'] == 'high'][:5]
    rel_mems = recall(user_message, limit=3)
    imp_mems = get_important_memories(limit=3)
    
    # deduplicate memories
    seen = set()
    final_mems = []
    for m in rel_mems + imp_mems:
        if m['id'] not in seen:
            seen.add(m['id'])
            final_mems.append(m)
            
    context = ""
    if high_priority:
        context += "High priority tasks:\n" + "\n".join([f"- {t['title']} (Due: {t['due_date']})" for t in high_priority]) + "\n"
    if final_mems:
        context += "Relevant memories:\n" + "\n".join([f"- {m['content']}" for m in final_mems]) + "\n"
    return context

def format_tasks_for_voice(tasks: List[Dict]) -> str:
    if not tasks:
        return "No tasks on the list, sir."
    if len(tasks) == 1:
        return f"One task: {tasks[0]['title']}."
    high_count = len([t for t in tasks if t['priority'] == 'high'])
    top3 = [t['title'] for t in tasks[:3]]
    res = f"You have {len(tasks)} open tasks."
    if high_count > 0:
        res += f" {high_count} of them are high priority."
    res += f" Top items include {', '.join(top3)}."
    return res

def format_plan_for_voice(tasks: List[Dict], events: List[Dict]) -> str:
    parts = []
    if not events:
        parts.append("Your schedule is clear today.")
    else:
        parts.append(f"You have {len(events)} events today.")
        
    if not tasks:
        parts.append("And no pending tasks.")
    else:
        parts.append(f"And {len(tasks)} tasks.")
    return " ".join(parts)

async def extract_memories(user_text: str, jarvis_response: str):
    if len(user_text) <= 15:
        return []
    prompt = f"""
    Extract CONCRETE facts about the user from the following conversation snippet.
    Focus on preferences, decisions, names, dates, plans, goals. Do not include casual chat.
    Return ONLY a JSON array of objects with keys: type (fact/preference/project/person/decision), content, importance (1-10), source (user).
    ONLY output valid JSON, nothing else.
    
    User: {user_text}
    JARVIS: {jarvis_response}
    """
    try:
        import httpx, re
        async with httpx.AsyncClient(timeout=20.0) as client:
            res = await client.post(
                "https://text.pollinations.ai/",
                json={"messages": [{"role": "user", "content": prompt}], "jsonMode": True},
                headers={"Content-Type": "application/json"}
            )
            content = res.text
            json_match = re.search(r'\[.*\]', content, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                memories_extracted = []
                for mem in data:
                    remember(mem.get('content'), mem.get('type', 'fact'), 'conversation', mem.get('importance', 5))
                    memories_extracted.append(mem.get('content'))
                return memories_extracted
    except Exception as e:
        pass
    return []

init_db()
