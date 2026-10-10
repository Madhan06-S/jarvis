"""
JARVIS MEMORY TIMELINE SYSTEM
Holographic memory timeline — searchable, visual, contextual.
Extends the existing memory.py with timeline visualization data.
"""
import time
import json
import sqlite3
from typing import List, Dict, Optional
from memory import get_connection, DB_PATH


def get_timeline(limit: int = 50, filter_type: Optional[str] = None) -> List[Dict]:
    """Get memories as a timeline with visual metadata."""
    conn = get_connection()
    c = conn.cursor()

    query = "SELECT * FROM memories"
    params = []
    if filter_type:
        query += " WHERE type = ?"
        params.append(filter_type)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    c.execute(query, params)
    rows = [dict(row) for row in c.fetchall()]
    conn.close()

    # Enrich with visual metadata
    for i, row in enumerate(rows):
        row["visual"] = _get_visual_meta(row, i)
        row["age_label"] = _age_label(row["created_at"])

    return rows


def get_knowledge_graph(limit: int = 30) -> Dict:
    """Build a knowledge graph from memories for visualization."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM memories ORDER BY importance DESC, last_accessed DESC LIMIT ?", (limit,))
    memories = [dict(row) for row in c.fetchall()]
    conn.close()

    nodes = []
    edges = []
    seen_words = {}

    for mem in memories:
        node_id = f"mem_{mem['id']}"
        nodes.append({
            "id":       node_id,
            "label":    mem["content"][:40],
            "type":     mem["type"],
            "size":     5 + mem["importance"],
            "color":    _type_color(mem["type"]),
            "full":     mem["content"],
            "time":     mem["created_at"],
        })

        # Connect memories that share keywords
        words = set(mem["content"].lower().split())
        for word in words:
            if len(word) > 4:
                if word in seen_words:
                    for other_id in seen_words[word][:3]:
                        edge_key = tuple(sorted([node_id, other_id]))
                        if edge_key not in [tuple(sorted([e["from"], e["to"]])) for e in edges]:
                            edges.append({"from": node_id, "to": other_id, "weight": 1})
                    seen_words[word].append(node_id)
                else:
                    seen_words[word] = [node_id]

    return {"nodes": nodes, "edges": edges[:100]}


def get_conversation_history(limit: int = 20) -> List[Dict]:
    """Get recent conversation history formatted for timeline."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT * FROM memories 
        WHERE source = 'conversation' 
        ORDER BY created_at DESC 
        LIMIT ?
    """, (limit,))
    rows = [dict(row) for row in c.fetchall()]
    conn.close()
    return rows


def search_timeline(query: str, limit: int = 20) -> List[Dict]:
    """Full-text search across all memory types."""
    from memory import recall, search_tasks, search_notes
    results = []

    mems  = recall(query, limit=limit // 3)
    tasks = search_tasks(query, limit=limit // 3)
    notes = search_notes(query, limit=limit // 3)

    for m in mems:
        m["_source_type"] = "memory"
        results.append(m)
    for t in tasks:
        t["_source_type"] = "task"
        results.append(t)
    for n in notes:
        n["_source_type"] = "note"
        results.append(n)

    return results


def get_stats() -> Dict:
    """Get memory system statistics."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) as total, type FROM memories GROUP BY type")
    by_type = {row["type"]: row["total"] for row in c.fetchall()}

    c.execute("SELECT COUNT(*) as total FROM tasks WHERE status = 'open'")
    open_tasks = c.fetchone()["total"]

    c.execute("SELECT COUNT(*) as total FROM notes")
    total_notes = c.fetchone()["total"]

    c.execute("SELECT AVG(importance) as avg_imp FROM memories")
    avg_imp = c.fetchone()["avg_imp"] or 0

    conn.close()

    return {
        "memories_by_type": by_type,
        "total_memories":   sum(by_type.values()),
        "open_tasks":       open_tasks,
        "total_notes":      total_notes,
        "avg_importance":   round(avg_imp, 1),
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_visual_meta(mem: Dict, index: int) -> Dict:
    """Generate visual positioning and styling for timeline node."""
    type_colors = {
        "fact":       "#00BFFF",
        "preference": "#00ff88",
        "project":    "#ffcc00",
        "person":     "#ff8800",
        "decision":   "#cc44ff",
        "goal":       "#ff4444",
    }
    return {
        "color":    type_colors.get(mem.get("type", "fact"), "#00BFFF"),
        "size":     max(8, min(24, mem.get("importance", 5) * 2)),
        "glow":     mem.get("importance", 5) > 7,
        "position": index,
    }


def _type_color(mem_type: str) -> str:
    colors = {
        "fact":       "#00BFFF",
        "preference": "#00ff88",
        "project":    "#ffcc00",
        "person":     "#ff8800",
        "decision":   "#cc44ff",
        "goal":       "#ff4444",
        "conversation": "#aaaaff",
    }
    return colors.get(mem_type, "#00BFFF")


def _age_label(timestamp: float) -> str:
    age = time.time() - timestamp
    if age < 3600:
        return f"{int(age/60)}m ago"
    elif age < 86400:
        return f"{int(age/3600)}h ago"
    elif age < 604800:
        return f"{int(age/86400)}d ago"
    else:
        return f"{int(age/604800)}w ago"
