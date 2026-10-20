"""
JARVIS UI Control Skill
Control HUD theme colors, reactor style/speed/scale, chrome furniture, screen clearing, and visual effects.
"""
import re
import json
from typing import Dict, Any, Optional

NAME = "UI Control"
DESCRIPTION = "Voice control for HUD theme colors, reactor style/speed, chrome furniture, screen clearing, and effects"
TRIGGERS = [
    "ui theme", "retint", "accent color", "change theme", "ui color",
    "ui reactor", "reactor style", "reactor speed", "reactor scale", "reactor color",
    "ui chrome", "hide chrome", "show chrome", "hide sidebar", "show sidebar",
    "ui effect", "glitch", "pulse effect", "scan effect", "shake screen", "flash screen",
    "ui reset", "reset theme", "reset interface", "stock theme",
    "clear screen", "ui screen", "clear panels"
]

COLOR_MAP = {
    "red": "#ff2d2d",
    "crimson": "#dc143c",
    "green": "#00ff88",
    "emerald": "#50c878",
    "blue": "#0088ff",
    "cyan": "#00BFFF",
    "amber": "#ffaa00",
    "gold": "#ffd700",
    "purple": "#9d4edd",
    "violet": "#c77dff",
    "orange": "#ff6600",
    "white": "#e0f2fe",
    "stock": "auto",
    "default": "auto",
    "reset": "auto",
}

async def send_ws(websocket, payload: Dict[str, Any]):
    if websocket:
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            print(f"[UI Skill] WebSocket send error: {e}")

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()

    # 1. Reset
    if any(k in t for k in ["ui reset", "reset theme", "reset interface", "stock theme", "default theme"]):
        payload = {"type": "ui", "op": "reset", "args": {}}
        await send_ws(websocket, payload)
        return {
            "handled": True,
            "spoken_response": "Restoring interface and arc reactor to stock settings.",
            "hud_card": {
                "type": "ui_control",
                "title": "SYSTEM RESTORE",
                "data": {"action": "reset", "detail": "Interface returned to default theme."}
            },
            "action": payload
        }

    # 2. Clear Screen / Panels
    if any(k in t for k in ["clear screen", "ui screen", "clear panels", "wipe screen"]):
        what = "panels" if "panel" in t else "all"
        payload = {"type": "ui", "op": "screen", "args": {"what": what}}
        await send_ws(websocket, payload)
        return {
            "handled": True,
            "spoken_response": f"Clearing {what} from the display.",
            "hud_card": {
                "type": "ui_control",
                "title": "DISPLAY CLEARED",
                "data": {"cleared": what}
            },
            "action": payload
        }

    # 3. Effects: glitch, pulse, scan, shake, flash
    for fx in ["glitch", "pulse", "scan", "shake", "flash"]:
        if fx in t:
            payload = {"type": "ui", "op": "effect", "args": {"kind": fx}}
            await send_ws(websocket, payload)
            return {
                "handled": True,
                "spoken_response": f"Triggering {fx} sequence across HUD.",
                "hud_card": {
                    "type": "ui_control",
                    "title": f"VISUAL EFFECT: {fx.upper()}",
                    "data": {"effect": fx}
                },
                "action": payload
            }

    # 4. Reactor Controls: style (ring, sphere, wire), scale, speed/spin, color
    if any(k in t for k in ["reactor", "arc reactor"]):
        reactor_args = {}

        # Style
        if "sphere" in t:
            reactor_args["style"] = "sphere"
        elif "wire" in t or "lattice" in t or "skeletal" in t:
            reactor_args["style"] = "wire"
        elif "ring" in t:
            reactor_args["style"] = "ring"

        # Spin / speed
        spin_match = re.search(r"(?:speed|spin)\s*(?:to|=)?\s*([\d\.]+)", t)
        if spin_match:
            try:
                reactor_args["spin"] = max(0.0, min(5.0, float(spin_match.group(1))))
            except ValueError:
                pass
        elif "fast" in t:
            reactor_args["spin"] = 2.5
        elif "slow" in t:
            reactor_args["spin"] = 0.5
        elif "stop" in t or "freeze" in t:
            reactor_args["spin"] = 0.0

        # Scale
        scale_match = re.search(r"scale\s*(?:to|=)?\s*([\d\.]+)", t)
        if scale_match:
            try:
                reactor_args["scale"] = max(0.2, min(3.0, float(scale_match.group(1))))
            except ValueError:
                pass
        elif "big" in t or "large" in t:
            reactor_args["scale"] = 1.6
        elif "small" in t or "tiny" in t:
            reactor_args["scale"] = 0.7

        # Color
        for c_name, c_hex in COLOR_MAP.items():
            if c_name in t:
                reactor_args["color"] = None if c_hex == "auto" else c_hex
                break

        if reactor_args:
            payload = {"type": "ui", "op": "patch", "args": {"reactor": reactor_args}}
            await send_ws(websocket, payload)
            spoken = "Adjusting arc reactor properties."
            if "style" in reactor_args:
                spoken = f"Arc reactor set to {reactor_args['style']} mode."
            elif "spin" in reactor_args:
                spoken = f"Arc reactor rotation speed adjusted to {reactor_args['spin']}x."
            return {
                "handled": True,
                "spoken_response": spoken,
                "hud_card": {
                    "type": "ui_control",
                    "title": "ARC REACTOR TUNING",
                    "data": reactor_args
                },
                "action": payload
            }

    # 5. Chrome controls: sidebar, systems, transcript
    if any(k in t for k in ["chrome", "sidebar", "workspace", "furniture"]):
        hide = any(w in t for w in ["hide", "close", "disable", "off", "remove"])
        chrome_args = {}
        if "sidebar" in t or "workspace" in t:
            chrome_args["workspace"] = not hide
        if "systems" in t or "rail" in t:
            chrome_args["systems"] = not hide
        if "transcript" in t or "chat" in t:
            chrome_args["transcript"] = not hide

        if not chrome_args:
            chrome_args["workspace"] = not hide

        payload = {"type": "ui", "op": "patch", "args": {"chrome": chrome_args}}
        await send_ws(websocket, payload)
        state_str = "hidden" if hide else "visible"
        return {
            "handled": True,
            "spoken_response": f"HUD furniture updated: set to {state_str}.",
            "hud_card": {
                "type": "ui_control",
                "title": "CHROME VISIBILITY",
                "data": chrome_args
            },
            "action": payload
        }

    # 6. Theme retint / accent color
    chosen_color = None
    hex_match = re.search(r"#(?:[0-9a-fA-F]{3}){1,2}\b", query)
    if hex_match:
        chosen_color = hex_match.group(0)
    else:
        for c_name, c_hex in COLOR_MAP.items():
            if c_name in t:
                chosen_color = None if c_hex == "auto" else c_hex
                break

    if chosen_color is not None or "reset" in t or "default" in t:
        theme_patch = {"accent": chosen_color}
        payload = {"type": "ui", "op": "patch", "args": theme_patch}
        await send_ws(websocket, payload)
        spoken = f"HUD retinted with new accent palette." if chosen_color else "HUD color restored to default."
        return {
            "handled": True,
            "spoken_response": spoken,
            "hud_card": {
                "type": "ui_control",
                "title": "THEME RETINT",
                "data": {"accent": chosen_color or "default"}
            },
            "action": payload
        }

    return {"handled": False}
