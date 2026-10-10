"""
JARVIS Workflow Automation Skill (workflows.yaml)
"""
import os
import re
import yaml
import subprocess
from typing import Dict, Any

NAME = "Project Workflows"
DESCRIPTION = "Automate project startup: opens VS Code, launches dev servers, and opens browser URLs"
TRIGGERS = ["start work on", "work on", "open project", "launch workflow", "start project"]

def _load_workflows() -> Dict[str, Any]:
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "workflows.yaml")
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return data.get("workflows", {})
        except Exception as e:
            print(f"[Workflow Skill] YAML load error: {e}")
    return {}

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()
    workflows = _load_workflows()

    m = re.search(r"(?:start\s+work\s+on|work\s+on|open\s+project|launch\s+workflow|start\s+project)\s+([a-zA-Z0-9_\-]+)", t)
    proj_key = m.group(1).strip() if m else ""

    # Match closest project key
    target_wf = None
    matched_name = ""
    for k, wf in workflows.items():
        if proj_key in k.lower() or k.lower() in t:
            target_wf = wf
            matched_name = k
            break

    if not target_wf:
        available = ", ".join(workflows.keys()) if workflows else "None defined"
        return {
            "handled": True,
            "spoken_response": f"Project not found. Defined workflows: {available}.",
            "hud_card": None
        }

    proj_path = target_wf.get("path")
    editor = target_wf.get("editor", "code")
    url = target_wf.get("url")

    # 1. Open VS Code / Editor
    if proj_path and os.path.exists(proj_path):
        subprocess.Popen([editor, proj_path])

    # 2. Open URL in browser
    if url:
        subprocess.Popen(["open", url])

    spoken = f"Initiating workflow for {matched_name}. Opening VS Code and launching project URL."

    return {
        "handled": True,
        "spoken_response": spoken,
        "hud_card": {
            "type": "workflow",
            "title": f"WORKFLOW — {matched_name.upper()}",
            "data": {
                "project": matched_name,
                "path": proj_path,
                "url": url,
                "status": "Launched"
            }
        }
    }
