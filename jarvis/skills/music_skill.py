"""
JARVIS Music Skill — Enhanced YouTube IFrame & yt-dlp Audio Integration
"""
import os
import re
import json
import subprocess
import urllib.parse
import webbrowser
from typing import Dict, Any, Optional

NAME = "Music"
DESCRIPTION = "Play songs with YouTube IFrame API mini player, working controls, and yt-dlp search"
TRIGGERS = [
    "play", "play music", "play song", "music", 
    "pause music", "stop music", "pause", "stop",
    "resume", "resume music", "continue music",
    "next track", "next song", "skip song", 
    "volume up", "volume down", "louder", "softer", "turn up volume", "turn down volume"
]

def search_youtube_ytdlp(query: str) -> Dict[str, Any]:
    """
    Search YouTube using yt-dlp to extract video_id, title, uploader, and webpage URL.
    Prints detailed, verbose search logs directly to the backend terminal.
    """
    print(f"\n==================================================")
    print(f"🎵 [MUSIC SKILL LOG] Search request: '{query}'")
    print(f"==================================================")

    # Locate yt-dlp binary
    import shutil
    import sys
    ytdlp_path = shutil.which("yt-dlp") or os.path.join(os.path.dirname(sys.executable), "yt-dlp")
    if not os.path.exists(ytdlp_path):
        ytdlp_path = "yt-dlp"

    try:
        cmd = [ytdlp_path, "--dump-json", f"ytsearch1:{query}"]
        print(f"DEBUG :: Executing subprocess command: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        
        if res.returncode == 0 and res.stdout.strip():
            data = json.loads(res.stdout)
            video_id = data.get("id")
            title = data.get("title", query.title())
            uploader = data.get("uploader", "YouTube")
            web_url = data.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}"
            
            print(f"SUCCESS :: Search result retrieved from yt-dlp:")
            print(f"  ├── Query:     '{query}'")
            print(f"  ├── Video ID:  {video_id}")
            print(f"  ├── Title:     {title}")
            print(f"  ├── Uploader:  {uploader}")
            print(f"  └── Watch URL: {web_url}")
            print(f"==================================================\n")
            
            return {
                "video_id": video_id,
                "title": title,
                "uploader": uploader,
                "url": web_url,
                "error": None
            }
        else:
            err_msg = res.stderr.strip() if res.stderr else f"Exit code {res.returncode}"
            print(f"WARNING :: yt-dlp search returned error: {err_msg}")
    except Exception as err:
        print(f"ERROR :: Exception during yt-dlp search for '{query}': {err}")

    # Fallback to direct search URL or Interstellar default
    fallback_id = "UDVtMYqUAyw" # Interstellar Main Theme default
    fallback_url = f"https://www.youtube.com/watch?v={fallback_id}"
    print(f"FALLBACK :: Using fallback Video ID: {fallback_id}")
    print(f"==================================================\n")
    return {
        "video_id": fallback_id,
        "title": query.title() if query else "Interstellar Main Theme",
        "uploader": "Hans Zimmer",
        "url": fallback_url,
        "error": "yt-dlp search failed; using default fallback"
    }

async def run(query: str, websocket=None) -> Dict[str, Any]:
    t = query.lower().strip()

    # 1. PAUSE / STOP MUSIC
    if any(k in t for k in ["pause music", "stop music", "pause", "stop"]):
        print("🎵 [MUSIC SKILL LOG] Command execution: PAUSE / STOP MUSIC")
        return {
            "handled": True,
            "spoken_response": "Pausing media playback, sir.",
            "hud_card": {
                "type": "music_control",
                "title": "MEDIA PLAYER",
                "data": {"action": "pause"}
            },
            "action": {"action": "RUN_COMMAND", "target": "osascript -e 'tell application \"System Events\" to key code 16'"}
        }

    # 2. RESUME MUSIC
    if any(k in t for k in ["resume music", "resume", "continue music"]):
        print("🎵 [MUSIC SKILL LOG] Command execution: RESUME MUSIC")
        return {
            "handled": True,
            "spoken_response": "Resuming music playback.",
            "hud_card": {
                "type": "music_control",
                "title": "MEDIA PLAYER",
                "data": {"action": "play"}
            },
            "action": {"action": "RUN_COMMAND", "target": "osascript -e 'tell application \"System Events\" to key code 16'"}
        }

    # 3. NEXT TRACK / SKIP
    if any(k in t for k in ["next track", "next song", "skip song"]):
        print("🎵 [MUSIC SKILL LOG] Command execution: NEXT TRACK")
        return {
            "handled": True,
            "spoken_response": "Skipping to the next track.",
            "hud_card": {
                "type": "music_control",
                "title": "MEDIA PLAYER",
                "data": {"action": "next"}
            },
            "action": {"action": "RUN_COMMAND", "target": "osascript -e 'tell application \"System Events\" to key code 19'"}
        }

    # 4. VOLUME UP / DOWN
    if any(k in t for k in ["volume up", "louder", "turn up volume"]):
        print("🎵 [MUSIC SKILL LOG] Command execution: VOLUME UP")
        return {
            "handled": True,
            "spoken_response": "Increasing volume.",
            "hud_card": {
                "type": "music_control",
                "title": "MEDIA PLAYER",
                "data": {"action": "volume_up"}
            },
            "action": {"action": "RUN_COMMAND", "target": "osascript -e 'set volume output volume ((output volume of (get volume settings)) + 15)'"}
        }

    if any(k in t for k in ["volume down", "softer", "turn down volume"]):
        print("🎵 [MUSIC SKILL LOG] Command execution: VOLUME DOWN")
        return {
            "handled": True,
            "spoken_response": "Lowering volume.",
            "hud_card": {
                "type": "music_control",
                "title": "MEDIA PLAYER",
                "data": {"action": "volume_down"}
            },
            "action": {"action": "RUN_COMMAND", "target": "osascript -e 'set volume output volume ((output volume of (get volume settings)) - 15)'"}
        }

    # 5. PLAY SONG (SEARCH & PLAY)
    song_query = re.sub(r"^(?:play|start|listen to)\s+", "", t, flags=re.IGNORECASE).strip()
    if not song_query or song_query in ["music", "song"]:
        song_query = "Interstellar theme"

    res = search_youtube_ytdlp(song_query)
    video_id = res["video_id"]
    title = res["title"]
    url = res["url"]

    spoken = f"Playing {title} on the HUD player."

    # Fallback to browser only if no HUD client is connected
    if websocket is None:
        try:
            print(f"🎵 [MUSIC SKILL LOG] No HUD client attached. Opening browser fallback: {url}")
            webbrowser.open(url)
        except Exception as e:
            print(f"🎵 [MUSIC SKILL LOG] Browser fallback warning: {e}")

    return {
        "handled": True,
        "spoken_response": spoken,
        "hud_card": {
            "type": "music",
            "title": "STARK MEDIA PLAYER",
            "data": {
                "video_id": video_id,
                "title": title,
                "uploader": res["uploader"],
                "url": url,
                "status": "playing"
            }
        },
        "action": None
    }

