"""
ANTIGRAVITY JARVIS — Modular Dynamic Skill-Based Intent Router
Automatically discovers, registers, and routes commands to python skills in jarvis/skills/
"""
import os
import re
import time
import glob
import importlib.util
from typing import Dict, Any, List, Optional

SKILLS: List[Any] = []
SKILLS_MANIFEST: List[Dict[str, Any]] = []

def load_skills():
    """Dynamically loads all skill modules from the jarvis/skills/ directory."""
    global SKILLS, SKILLS_MANIFEST
    SKILLS.clear()
    SKILLS_MANIFEST.clear()

    skills_dir = os.path.join(os.path.dirname(__file__), "skills")
    if not os.path.exists(skills_dir):
        os.makedirs(skills_dir, exist_ok=True)
        return

    pattern = os.path.join(skills_dir, "*_skill.py")
    skill_files = glob.glob(pattern)

    for filepath in sorted(skill_files):
        mod_name = os.path.basename(filepath)[:-3]
        try:
            spec = importlib.util.spec_from_file_location(f"jarvis.skills.{mod_name}", filepath)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                
                name = getattr(mod, "NAME", mod_name.replace("_skill", "").capitalize())
                desc = getattr(mod, "DESCRIPTION", "JARVIS skill module")
                triggers = getattr(mod, "TRIGGERS", [])
                
                if hasattr(mod, "run"):
                    SKILLS.append(mod)
                    SKILLS_MANIFEST.append({
                        "name": name,
                        "description": desc,
                        "triggers": triggers,
                        "file": mod_name
                    })
                    print(f"[Skills Manager] Loaded skill: {name} ({len(triggers)} triggers)")
        except Exception as err:
            print(f"[Skills Manager] Failed to load skill {filepath}: {err}")

load_skills()

def get_all_skills_manifest() -> List[Dict[str, Any]]:
    """Returns list of registered skills for HUD manifest rendering."""
    return SKILLS_MANIFEST

async def route_intent_fast(user_text: str, websocket=None) -> Optional[Dict[str, Any]]:
    """
    Evaluates query against loaded skills.
    Returns result dict if a skill handles it, or None to fall back to LLM.
    """
    t = user_text.lower().strip()

    # Special command: /skills
    if t in ["/skills", "skills", "list skills", "what can you do", "show skills"]:
        skills_text = f"I currently have {len(SKILLS_MANIFEST)} active skill modules online: " + ", ".join([s['name'] for s in SKILLS_MANIFEST])
        return {
            "is_fast": True,
            "intent": "SKILLS_MANIFEST",
            "spoken_response": skills_text,
            "hud_card": {
                "type": "skills_manifest",
                "title": "ACTIVE SKILL MODULES",
                "data": SKILLS_MANIFEST
            },
            "action": None
        }

    # Evaluate registered skills
    for skill in SKILLS:
        triggers = getattr(skill, "TRIGGERS", [])
        for trig in triggers:
            # Check keyword match
            if re.search(r"\b" + re.escape(trig) + r"\b", t):
                try:
                    res = await skill.run(user_text, websocket)
                    if res and res.get("handled"):
                        return {
                            "is_fast": True,
                            "intent": getattr(skill, "NAME", "SKILL"),
                            "spoken_response": res.get("spoken_response", "Command executed."),
                            "hud_card": res.get("hud_card"),
                            "action": res.get("action")
                        }
                except Exception as e:
                    print(f"[Skills Manager] Error running {getattr(skill, 'NAME', 'skill')}: {e}")

    return None
