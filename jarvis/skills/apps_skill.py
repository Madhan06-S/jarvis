"""
JARVIS Applications & Websites Skill
"""
import re
import urllib.parse
from typing import Dict, Any

NAME = "Apps & Web"
DESCRIPTION = "Launch installed apps, websites (YouTube, Gmail, Maps, VS Code, Chrome) and web searches"
TRIGGERS = ["open", "launch", "start", "go to", "search", "google", "search google for"]

APP_MAP = {
    "youtube": ("https://youtube.com", True),
    "gmail": ("https://mail.google.com", True),
    "mail": ("https://mail.google.com", True),
    "maps": ("https://maps.google.com", True),
    "google maps": ("https://maps.google.com", True),
    "github": ("https://github.com", True),
    "spotify": ("https://open.spotify.com", True),
    "vs code": ("Visual Studio Code", False),
    "vscode": ("Visual Studio Code", False),
    "code": ("Visual Studio Code", False),
    "chrome": ("Google Chrome", False),
    "browser": ("Google Chrome", False),
    "safari": ("Safari", False),
    "terminal": ("Terminal", False),
    "calculator": ("Calculator", False),
    "finder": ("Finder", False),
}

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()

    # Google search handling
    m_search = re.search(r"(?:search\s+google\s+for|search\s+for|google)\s+(.+)", t)
    if m_search:
        search_q = m_search.group(1).strip()
        encoded = urllib.parse.quote(search_q)
        url = f"https://google.com/search?q={encoded}"
        return {
            "handled": True,
            "spoken_response": f"Searching Google for {search_q}.",
            "hud_card": None,
            "action": {"action": "OPEN_URL", "target": url}
        }

    # App or Website open
    m_open = re.search(r"(?:open|launch|start|go to)\s+(.+)", t)
    if m_open:
        target_raw = m_open.group(1).strip()
        
        # Check explicit mappings
        if target_raw in APP_MAP:
            target_val, is_url = APP_MAP[target_raw]
            if is_url:
                return {
                    "handled": True,
                    "spoken_response": f"Opening {target_raw.capitalize()}.",
                    "action": {"action": "OPEN_URL", "target": target_val}
                }
            else:
                return {
                    "handled": True,
                    "spoken_response": f"Launching {target_raw.capitalize()}.",
                    "action": {"action": "RUN_COMMAND", "target": f"open -a '{target_val}'"}
                }

        # Fallback to general URL or open command
        if "." in target_raw and not " " in target_raw:
            url = f"https://{target_raw}" if not target_raw.startswith("http") else target_raw
            return {
                "handled": True,
                "spoken_response": f"Opening {target_raw}.",
                "action": {"action": "OPEN_URL", "target": url}
            }

        return {
            "handled": True,
            "spoken_response": f"Launching {target_raw.capitalize()}.",
            "action": {"action": "RUN_COMMAND", "target": f"open -a '{target_raw}'"}
        }

    return {"handled": False}
