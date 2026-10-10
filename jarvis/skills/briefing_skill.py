"""
JARVIS Daily Briefing Skill — Weather, To-Do, Reminders & Git Status
"""
import os
import subprocess
import sqlite3
import httpx
from typing import Dict, Any

NAME = "Daily Briefing"
DESCRIPTION = "Comprehensive briefing on Weather, To-Dos, Reminders, and Workspace Git Status"
TRIGGERS = ["briefing", "daily briefing", "morning briefing", "give me my briefing", "status update"]

async def run(query: str, websocket=None) -> Dict[str, Any]:
    # 1. Weather
    temp_str, cond_str = "24°C", "Clear"
    try:
        from skills import weather_skill
        w_res = await weather_skill.run("weather in Mumbai")
        if w_res.get("hud_card"):
            temp_str = w_res["hud_card"]["data"]["temp"]
            cond_str = w_res["hud_card"]["data"]["condition"]
    except Exception:
        pass

    # 2. To-Do Items
    todos = []
    try:
        conn = sqlite3.connect("data/todos.db")
        c = conn.cursor()
        c.execute("SELECT task FROM todos WHERE status='pending' LIMIT 5")
        todos = [r[0] for r in c.fetchall()]
        conn.close()
    except Exception:
        pass

    # 3. Workspace Git Status
    workspace_dir = "/Users/madhan/Downloads/projects/ironnn"
    git_reports = []
    if os.path.exists(workspace_dir):
        for entry in os.listdir(workspace_dir):
            p = os.path.join(workspace_dir, entry)
            if os.path.isdir(p) and os.path.exists(os.path.join(p, ".git")):
                try:
                    res = subprocess.run(["git", "status", "-s"], cwd=p, capture_output=True, text=True, timeout=2)
                    lines = res.stdout.strip().split("\n") if res.stdout else []
                    changes_count = len([l for l in lines if l.strip()])
                    git_reports.append({"repo": entry, "changes": changes_count})
                except Exception:
                    pass

    git_summary = ", ".join([f"{g['repo']}: {g['changes']} pending changes" for g in git_reports if g['changes'] > 0])
    if not git_summary:
        git_summary = "All workspace repositories are clean."

    spoken = (
        f"Good day sir! Weather is {temp_str} with {cond_str.lower()}. "
        f"You have {len(todos)} active to-do items. Workspace status: {git_summary}"
    )

    return {
        "handled": True,
        "spoken_response": spoken,
        "hud_card": {
            "type": "briefing",
            "title": "STARK DAILY BRIEFING",
            "data": {
                "weather": f"{temp_str} — {cond_str}",
                "todos": todos if todos else ["No pending tasks"],
                "git": git_reports
            }
        }
    }
