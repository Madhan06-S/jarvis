"""
JARVIS System Control Skill — Hardware Controls & Safety Verification
"""
import re
import os
import subprocess
from typing import Dict, Any

NAME = "System Control"
DESCRIPTION = "Adjust volume, brightness, take screenshots, lock screen, and safe system execution"
TRIGGERS = ["volume", "mute", "unmute", "brightness", "screenshot", "lock screen", "lock computer", "shutdown", "restart", "reboot"]

DESTRUCTIVE_KEYWORDS = ["shutdown", "restart", "reboot", "format", "delete all", "rm -rf"]

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()

    # Safety Confirmation Check for Destructive Commands
    if any(dk in t for dk in DESTRUCTIVE_KEYWORDS):
        return {
            "handled": True,
            "spoken_response": "Warning, sir. That is a critical system operation. Please confirm if you wish to proceed.",
            "hud_card": {
                "type": "warning",
                "title": "CONFIRMATION REQUIRED",
                "data": f"Operation '{query}' requires explicit confirmation."
            },
            "action": None
        }

    # Volume Control
    v_match = re.search(r"(?:set|change)?\s*volume\s+(?:to\s+)?(\d+)", t)
    if v_match:
        val = max(0, min(100, int(v_match.group(1))))
        return {
            "handled": True,
            "spoken_response": f"Volume set to {val} percent.",
            "action": {"action": "VOLUME", "target": val}
        }

    if "mute" in t:
        return {
            "handled": True,
            "spoken_response": "Muting system audio.",
            "action": {"action": "VOLUME", "target": 0}
        }

    # Brightness Control
    b_match = re.search(r"(?:set|change)?\s*brightness\s+(?:to\s+)?(\d+)", t)
    if b_match:
        val = max(0, min(100, int(b_match.group(1))))
        # macOS brightness via osascript or brightness CLI
        cmd = f"osascript -e 'tell application \"System Events\" to set brightness to {val / 100.0}'"
        return {
            "handled": True,
            "spoken_response": f"Brightness set to {val} percent.",
            "action": {"action": "RUN_COMMAND", "target": cmd}
        }

    # Screenshot
    if "screenshot" in t or "screen capture" in t:
        shot_path = f"/tmp/screenshot_{int(os.path.getmtime(__file__))}.png"
        cmd = f"screencapture -x {shot_path}"
        return {
            "handled": True,
            "spoken_response": "Screen capture saved, sir.",
            "hud_card": {
                "type": "screenshot",
                "title": "SCREENSHOT CAPTURED",
                "data": shot_path
            },
            "action": {"action": "RUN_COMMAND", "target": cmd}
        }

    # Lock Screen
    if "lock" in t and ("screen" in t or "computer" in t or "mac" in t):
        cmd = "pmset displaysleepnow"
        return {
            "handled": True,
            "spoken_response": "Locking screen now.",
            "action": {"action": "RUN_COMMAND", "target": cmd}
        }

    return {"handled": False}
