"""
JARVIS Image Orbit Skill
Places vetted local images and generated artwork in 3D orbit around the arc reactor.
"""
import os
import re
import json
import glob
from typing import Dict, Any, Optional

NAME = "Image Orbit"
DESCRIPTION = "Places generated or local images into 3D orbital trajectory around the arc reactor"
TRIGGERS = [
    "orbit", "hang in orbit", "clear orbit", "clear orbits", "remove orbit", "orbit image", "add orbit"
]

_orbit_counter = 0

async def send_ws(websocket, payload: Dict[str, Any]):
    if websocket:
        try:
            await websocket.send_text(json.dumps(payload))
        except Exception as e:
            print(f"[Orbit Skill] WebSocket send error: {e}")

async def run(query: str, websocket=None) -> Dict[str, Any]:
    global _orbit_counter
    t = query.lower().strip()

    # 1. Clear Orbits
    if "clear" in t and ("orbit" in t or "all" in t):
        payload = {"type": "ui", "op": "orbit", "args": {"action": "clear"}}
        await send_ws(websocket, payload)
        return {
            "handled": True,
            "spoken_response": "Taking down all images from reactor orbit.",
            "hud_card": {
                "type": "orbit_control",
                "title": "ORBITS CLEARED",
                "data": {"action": "clear"}
            },
            "action": payload
        }

    # 2. Remove specific Orbit by ID
    remove_match = re.search(r"remove\s+orbit\s+([\w-]+)", t)
    if remove_match:
        target_id = remove_match.group(1)
        payload = {"type": "ui", "op": "orbit", "args": {"action": "remove", "id": target_id}}
        await send_ws(websocket, payload)
        return {
            "handled": True,
            "spoken_response": f"Removed orbital object {target_id}.",
            "hud_card": {
                "type": "orbit_control",
                "title": "ORBIT REMOVED",
                "data": {"id": target_id}
            },
            "action": payload
        }

    # 3. Add Orbit
    # Look for image path or filename in query
    path_match = re.search(r"(?:image|path|file)?\s*([/\w\.\-~]+\.(?:png|jpg|jpeg|webp|gif))", query, re.IGNORECASE)
    src_path = None
    if path_match:
        candidate = os.path.expanduser(path_match.group(1).strip())
        if os.path.isabs(candidate) and os.path.exists(candidate):
            src_path = candidate
        else:
            # Check relative to cwd
            rel_candidate = os.path.abspath(candidate)
            if os.path.exists(rel_candidate):
                src_path = rel_candidate

    # If no path specified, search for recent generated images or screenshots in workspace
    if not src_path:
        search_dirs = [
            os.path.join(os.getcwd(), "data"),
            os.path.join(os.getcwd(), "frontend", "public"),
            os.path.expanduser("~/Desktop"),
        ]
        candidates = []
        for d in search_dirs:
            if os.path.exists(d):
                for ext in ["*.png", "*.jpg", "*.webp"]:
                    candidates.extend(glob.glob(os.path.join(d, ext)))
        if candidates:
            # Sort by newest
            candidates.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            src_path = candidates[0]
        else:
            # Fallback icon/asset
            src_path = os.path.abspath("frontend/public/icon-192.png")

    _orbit_counter += 1
    orbit_id = f"orbit-{_orbit_counter}"

    # Parse speed or radius if present
    speed = 4.0
    if "fast" in t:
        speed = 8.0
    elif "slow" in t:
        speed = 2.0
    elif "reverse" in t or "counter" in t:
        speed = -4.0

    args = {
        "action": "add",
        "id": orbit_id,
        "src": src_path,
        "radius": 0.55,
        "speed": speed,
        "size": 96,
        "tilt": 24,
        "opacity": 0.9,
        "phase": (_orbit_counter * 137.5) % 360
    }

    payload = {"type": "ui", "op": "orbit", "args": args}
    await send_ws(websocket, payload)

    img_name = os.path.basename(src_path) if src_path else "graphic"
    return {
        "handled": True,
        "spoken_response": f"Placing {img_name} into orbital trajectory around the reactor.",
        "hud_card": {
            "type": "orbit_control",
            "title": "IMAGE ORBIT ACTIVE",
            "data": {
                "id": orbit_id,
                "file": img_name,
                "speed": f"{speed} rpm",
                "status": "In stable orbit"
            }
        },
        "action": payload
    }
