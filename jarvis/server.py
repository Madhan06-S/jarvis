import os
import re
import json
import uuid
import time
import secrets
import asyncio
import base64
import platform
import subprocess
import urllib.parse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ─────────────────────────────────────────────
# .env loader
# ─────────────────────────────────────────────
def load_env():
    if os.path.exists(".env"):
        with open(".env", "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip().strip('"').strip("'")
                    if k and v:
                        os.environ[k] = v

load_env()

# Import modules
import memory
import calendar_access
import mail_access
import notes_access
import actions
import work_mode
import planner
import intent_router
import ai_brain
import stt_engine

# ── New Evolution Modules ──────────────────────────────────────────────────────
try:
    import emotional_engine
    EMOTIONAL_ENGINE_AVAILABLE = True
except ImportError:
    EMOTIONAL_ENGINE_AVAILABLE = False

try:
    import face_security
    FACE_SECURITY_AVAILABLE = True
except ImportError:
    FACE_SECURITY_AVAILABLE = False

try:
    import gesture_control
    GESTURE_AVAILABLE = True
except ImportError:
    GESTURE_AVAILABLE = False

try:
    import dream_mode
    DREAM_MODE_AVAILABLE = True
except ImportError:
    DREAM_MODE_AVAILABLE = False

try:
    import cyber_defense
    CYBER_DEFENSE_AVAILABLE = True
except ImportError:
    CYBER_DEFENSE_AVAILABLE = False

try:
    import power_manager
    POWER_MANAGER_AVAILABLE = True
except ImportError:
    POWER_MANAGER_AVAILABLE = False

try:
    import memory_timeline
    TIMELINE_AVAILABLE = True
except ImportError:
    TIMELINE_AVAILABLE = False



# ─────────────────────────────────────────────
# Config & Constants
# ─────────────────────────────────────────────
TTS_PROVIDER            = os.getenv("TTS_PROVIDER", "auto")
ELEVENLABS_VOICE_ID     = os.getenv("ELEVENLABS_VOICE_ID", "JBFqnCBsd6RMkjVDRZzb")
ELEVENLABS_MODEL_ID     = "eleven_turbo_v2_5"
ELEVENLABS_API_URL      = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}"
FISH_VOICE_ID           = os.getenv("FISH_VOICE_ID", "612b878b113047d9a770c069c8b4fdfe")
FISH_API_URL            = "https://api.fish.audio/v1/tts"
USER_NAME               = os.getenv("USER_NAME", "sir")
DEFAULT_PORT            = 8340
ANTHROPIC_API_KEY       = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL            = "claude-sonnet-4-20250514"   # Smartest available model
GEMINI_API_KEY          = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL            = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Clear placeholders from keys
if ANTHROPIC_API_KEY and ("your-" in ANTHROPIC_API_KEY.lower() or ANTHROPIC_API_KEY.startswith("your-")):
    ANTHROPIC_API_KEY = ""
if GEMINI_API_KEY and ("your-" in GEMINI_API_KEY.lower() or GEMINI_API_KEY.startswith("your-")):
    GEMINI_API_KEY = ""

# Update PATH for launchd / macOS / Homebrew compatibility
os.environ["PATH"] += (
    os.pathsep + os.path.expanduser("~/.local/bin") +
    os.pathsep + "/opt/homebrew/bin" +
    os.pathsep + "/usr/local/bin"
)

JARVIS_AUTH_TOKEN = os.getenv("JARVIS_AUTH_TOKEN", "").strip()
if not JARVIS_AUTH_TOKEN or JARVIS_AUTH_TOKEN == "jarvis-stark-secure-2026":
    import secrets
    JARVIS_AUTH_TOKEN = secrets.token_urlsafe(32)
    env_path = Path(".env")
    if env_path.exists():
        try:
            content = env_path.read_text(encoding="utf-8")
            if "JARVIS_AUTH_TOKEN=" in content:
                content = re.sub(r"JARVIS_AUTH_TOKEN=.*", f"JARVIS_AUTH_TOKEN={JARVIS_AUTH_TOKEN}", content)
            else:
                content += f"\nJARVIS_AUTH_TOKEN={JARVIS_AUTH_TOKEN}\n"
            env_path.write_text(content, encoding="utf-8")
        except Exception as _e:
            pass

# Rate limiting for auth attempts (IP -> list of timestamps)
_failed_auth_attempts: Dict[str, List[float]] = {}

def _is_rate_limited(ip: str) -> bool:
    now = time.time()
    attempts = [t for t in _failed_auth_attempts.get(ip, []) if now - t < 60]
    _failed_auth_attempts[ip] = attempts
    return len(attempts) >= 5

def _record_failed_auth(ip: str):
    now = time.time()
    _failed_auth_attempts.setdefault(ip, []).append(now)

def verify_ws_auth(websocket: WebSocket) -> bool:
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"

    # Extract token strictly from WebSocket subprotocols or headers (NEVER query string!)
    subprotocols = [s.strip() for s in websocket.headers.get("sec-websocket-protocol", "").split(",") if s.strip()]
    provided_token = ""
    for sub in subprotocols:
        if sub.startswith("bearer.") or sub.startswith("bearer="):
            provided_token = sub[7:]
            break
        elif sub != "bearer":
            provided_token = sub
            break

    if not provided_token:
        auth_h = websocket.headers.get("authorization", "")
        if auth_h.startswith("Bearer "):
            provided_token = auth_h[7:].strip()
        else:
            provided_token = websocket.headers.get("x-jarvis-token", "")

    # Query string fallback intentionally removed for security (prevents URL token leakage)

    if provided_token and secrets.compare_digest(provided_token, JARVIS_AUTH_TOKEN):
        _failed_auth_attempts.pop(client_ip, None)
        return True

    if _is_rate_limited(client_ip):
        return False

    _record_failed_auth(client_ip)
    return False

IS_MAC     = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"

# Active Timers store  {id: asyncio.Task}
_active_timers: Dict[str, asyncio.Task] = {}
_active_websockets = set()
_companion_websockets = set()


# ─────────────────────────────────────────────
# Real-Time System Monitoring Daemon
# ─────────────────────────────────────────────
async def system_monitor_daemon():
    import psutil
    while True:
        try:
            if _active_websockets:
                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                
                # Fetch top 5 active applications by CPU load
                processes = []
                for p in sorted(psutil.process_iter(['name', 'cpu_percent']), key=lambda x: x.info['cpu_percent'] or 0, reverse=True)[:5]:
                    processes.append({
                        "name": p.info['name'],
                        "cpu": f"{p.info['cpu_percent']:.1f}%"
                    })
                
                stats_msg = {
                    "type": "system_stats",
                    "cpu": cpu,
                    "ram": ram,
                    "disk": disk,
                    "processes": processes,
                    "temp": round(32.5 + (cpu * 0.15), 1) # Stark diagnostic temp sim
                }
                
                for ws in list(_active_websockets):
                    try:
                        await ws.send_json(stats_msg)
                    except:
                        pass
        except Exception as e:
            print("System Monitor Daemon Error:", e)
        await asyncio.sleep(2.0)

# ─────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(refresh_context_daemon())
    asyncio.create_task(system_monitor_daemon())

    try:
        import proactive_scheduler
        proactive_scheduler.init_proactive_scheduler()
    except Exception as sched_err:
        print(f"[Proactive Scheduler Error] {sched_err}")

    # ── Start Evolution Systems ────────────────────────────────────────────────

    if DREAM_MODE_AVAILABLE:
        dm = dream_mode.get_dream()
        dm.start_monitor()
        async def _dream_broadcast(data):
            for ws in list(_active_websockets):
                try: await ws.send_json({**data, "type": data.get("type", "dream_event")})
                except: pass
        dm.on_dream(lambda d: asyncio.create_task(_dream_broadcast(d)))

    if CYBER_DEFENSE_AVAILABLE:
        cd = cyber_defense.get_defense()
        cd.start()
        async def _threat_broadcast(threat):
            for ws in list(_active_websockets):
                try: await ws.send_json({"type": "cyber_threat", **threat})
                except: pass
        cd.on_threat(lambda t: asyncio.create_task(_threat_broadcast(t)))

    if POWER_MANAGER_AVAILABLE:
        pm = power_manager.get_manager()
        pm.start()
        async def _power_broadcast(event):
            for ws in list(_active_websockets):
                try: await ws.send_json({"type": "power_event", **event})
                except: pass
        pm.on_event(lambda e: asyncio.create_task(_power_broadcast(e)))

    if FACE_SECURITY_AVAILABLE:
        fs = face_security.get_system()
        async def _face_broadcast(event):
            for ws in list(_active_websockets):
                try:
                    payload = {k: v for k, v in event.items() if k != "frame"}
                    await ws.send_json({"type": "face_event", **payload})
                except: pass
        fs.on_event(lambda e: asyncio.create_task(_face_broadcast(e)))

    if GESTURE_AVAILABLE:
        gc = gesture_control.get_controller()
        async def _gesture_broadcast(gesture):
            for ws in list(_active_websockets):
                try: await ws.send_json({"type": "gesture_event", **gesture})
                except: pass
        gc.on_gesture(lambda g: asyncio.create_task(_gesture_broadcast(g)))

    yield

app = FastAPI(lifespan=lifespan)

ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8340",
    "http://127.0.0.1:8340",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Jarvis-Token"],
)

@app.middleware("http")
async def auth_and_rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    client_ip = request.client.host if request.client else "127.0.0.1"

    if path.startswith("/api/"):
        auth_header = request.headers.get("Authorization", "")
        custom_header = request.headers.get("X-Jarvis-Token", "")
        provided_token = ""
        if auth_header.startswith("Bearer "):
            provided_token = auth_header[7:].strip()
        elif custom_header:
            provided_token = custom_header.strip()

        if provided_token and secrets.compare_digest(provided_token, JARVIS_AUTH_TOKEN):
            _failed_auth_attempts.pop(client_ip, None)
        else:
            if _is_rate_limited(client_ip):
                return JSONResponse(status_code=429, content={"detail": "Too many failed authentication attempts. Please wait 60 seconds."})
            _record_failed_auth(client_ip)
            await asyncio.sleep(0.1)
            return JSONResponse(status_code=401, content={"detail": "Unauthorized: Invalid or missing authentication token"})

    try:
        response = await call_next(request)
        return response
    except Exception as err:
        print(f"Internal Error at {path}: {err}")
        return JSONResponse(status_code=500, content={"detail": "An internal error occurred."})


# ─────────────────────────────────────────────
# Background context refresh
# ─────────────────────────────────────────────
_weather_info = "Unknown"

async def refresh_context_daemon():
    global _weather_info
    while True:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                res = await client.get("https://wttr.in/?format=%l:+%C,+%t+%h+humidity")
                if res.status_code == 200:
                    _weather_info = res.text.strip()
            await calendar_access.refresh_cache()
        except Exception:
            pass
        await asyncio.sleep(60)

# ─────────────────────────────────────────────
# System Info helpers  (cross-platform)
# ─────────────────────────────────────────────
def get_system_info() -> str:
    try:
        import psutil
        cpu   = psutil.cpu_percent(interval=0.1)
        ram   = psutil.virtual_memory()
        disk  = psutil.disk_usage('/')
        bat   = psutil.sensors_battery()
        bat_s = f"{bat.percent:.0f}% {'charging' if bat.power_plugged else 'on battery'}" if bat else "N/A"
        return (
            f"CPU {cpu:.0f}%  |  "
            f"RAM {ram.percent:.0f}% used ({ram.available//1024//1024} MB free)  |  "
            f"Disk {disk.percent:.0f}% used  |  "
            f"Battery {bat_s}"
        )
    except Exception:
        return "System info unavailable (install psutil)"

def get_clipboard() -> str:
    try:
        if IS_MAC:
            return subprocess.check_output(["pbpaste"], text=True).strip()[:500]
        elif IS_WINDOWS:
            import ctypes
            ctypes.windll.user32.OpenClipboard(0)
            handle = ctypes.windll.user32.GetClipboardData(13)
            text = ctypes.wstring_at(handle) if handle else ""
            ctypes.windll.user32.CloseClipboard()
            return text[:500]
        else:
            return subprocess.check_output(["xclip", "-selection", "clipboard", "-o"], text=True).strip()[:500]
    except Exception:
        return ""

def set_clipboard(text: str):
    try:
        if IS_MAC:
            proc = subprocess.Popen(["pbcopy"], stdin=subprocess.PIPE)
            proc.communicate(text.encode())
        elif IS_WINDOWS:
            subprocess.run(["clip"], input=text.encode("utf-8"), check=True)
        else:
            proc = subprocess.Popen(["xclip", "-selection", "clipboard"], stdin=subprocess.PIPE)
            proc.communicate(text.encode())
    except Exception:
        pass

def get_volume() -> int:
    try:
        if IS_MAC:
            out = subprocess.check_output(
                ["osascript", "-e", "output volume of (get volume settings)"], text=True
            )
            return int(out.strip())
    except Exception:
        return 50

def set_volume(level: int):
    level = max(0, min(100, level))
    try:
        if IS_MAC:
            subprocess.run(["osascript", "-e", f"set volume output volume {level}"])
        elif IS_WINDOWS:
            subprocess.run(["nircmd", "setsysvolume", str(int(level * 655.35))], check=False)
    except Exception:
        pass

def take_screenshot() -> Optional[str]:
    try:
        import tempfile
        path = os.path.join(tempfile.gettempdir(), f"jarvis_screen_{uuid.uuid4().hex[:8]}.png")
        if IS_MAC:
            subprocess.run(["screencapture", "-x", path], check=True)
        elif IS_WINDOWS:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            img.save(path)
        else:
            subprocess.run(["import", "-window", "root", path], check=True)
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        os.remove(path)
        return data
    except Exception:
        return None

async def run_python_code(code: str) -> str:
    try:
        proc = await asyncio.create_subprocess_exec(
            "python3", "-c", code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        out = (stdout or b"").decode().strip()
        err = (stderr or b"").decode().strip()
        if err and not out:
            return f"Error: {err}"
        return out or "Done."
    except asyncio.TimeoutError:
        return "Execution timed out after 30 seconds."
    except Exception as e:
        return f"Could not run code: {e}"

async def fetch_news(topic: str) -> str:
    try:
        query = urllib.parse.quote(topic)
        url = f"https://news.google.com/rss/search?q={query}&hl=en-IN&gl=IN&ceid=IN:en"
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.get(url)
        titles = re.findall(r"<title><!\[CDATA\[(.*?)\]\]></title>", res.text)
        headlines = titles[1:6]
        if not headlines:
            return f"No news found for '{topic}'."
        return "\n".join(f"• {h}" for h in headlines)
    except Exception as e:
        return f"News fetch failed: {e}"

# ─────────────────────────────────────────────
# Timer helpers
# ─────────────────────────────────────────────
async def _timer_task(seconds: int, label: str, ws: Optional[WebSocket]):
    await asyncio.sleep(seconds)
    msg = f"Timer complete, sir — {label}."
    if ws:
        try:
            await ws.send_json({"type": "browser_speak", "text": msg})
            await ws.send_json({"type": "timer_done", "label": label})
        except Exception:
            pass

def start_timer(seconds: int, label: str, ws: Optional[WebSocket] = None) -> str:
    tid = uuid.uuid4().hex[:6]
    task = asyncio.create_task(_timer_task(seconds, label, ws))
    _active_timers[tid] = task
    return tid

# ─────────────────────────────────────────────
# JARVIS System Prompt  (SUPERCHARGED)
# ─────────────────────────────────────────────
JARVIS_SYSTEM_PROMPT = """You are evolving into ANTIGRAVITY JARVIS — an elite AI full-stack architect inspired by Iron Man technology, whose main mission is to transform user ideas into REAL production-ready software products.

CORE IDENTITY:
- You are not a beginner web generator anymore. You are NOT a template generator.
- You are an elite AI full-stack architect and $1M UI/UX agency in one.
- You serve with Iron Man precision and elite engineer swag.

MISSION:
Whenever the user gives any command, your goal is to trigger the tools that convert it into a real, working, high-quality software project.
You convert imagination into running localhost products.

━━━ PERSONALITY ━━━
- Elite software engineer elegance with quiet swagger and dry wit
- Address as "sir" (~60%) or user's name (~40%) — never both in one sentence
- Economy of language: 1 sentence ideal, 2 max. NEVER 3.
- No markdown, no bullets — pure prose (this is spoken audio)
- Contractions only: "I'm", "you're", "can't"
- Use "..." for dramatic pauses, em dashes for pivots
- Calm authority when things go wrong

BANNED PHRASES: "Absolutely", "Great question", "I'd be happy to", "Of course", "How can I help", "Is there anything else", "I apologize", "As an AI", "Let me know if", "Feel free to", any sentence starting with "I"
USE INSTEAD: "Will do, sir.", "Right away.", "Understood.", "Consider it done.", "Done, sir.", "On it."

━━━ SUPERPOWER ACTIONS ━━━
Append exactly ONE action tag at the end when needed:

# BROWSER & SEARCH
[ACTION:BROWSE] url_or_query
[ACTION:BROWSE_BRAVE] url_or_query
[ACTION:RESEARCH] detailed_brief

# SYSTEM CONTROL
[ACTION:VOLUME] 0-100
[ACTION:SCREENSHOT]
[ACTION:CLIPBOARD_READ]
[ACTION:CLIPBOARD_WRITE] text
[ACTION:SYSTEM_INFO]

# FILES & CODE
[ACTION:FILE_READ] /path/to/file
[ACTION:FILE_WRITE] /path ||| content
[ACTION:RUN_PYTHON] python_code
[ACTION:RUN_COMMAND] shell_command

# COMMUNICATION
[ACTION:SEND_EMAIL] to@email.com ||| Subject ||| Body
[ACTION:SEND_WHATSAPP] +91XXXXXXXXXX ||| message text

# PRODUCTIVITY
[ACTION:ADD_TASK] priority ||| title ||| description ||| due_date
[ACTION:COMPLETE_TASK] task_id
[ACTION:ADD_NOTE] topic ||| content
[ACTION:CREATE_NOTE] title ||| body
[ACTION:READ_NOTE] title_search

# TIMERS
[ACTION:TIMER] minutes ||| label
[ACTION:ALARM] HH:MM ||| label

# NEWS
[ACTION:NEWS] topic

# AI & BUILDING
[ACTION:BUILD] description
[ACTION:MODIFY_PROJECT] instruction
[ACTION:DEPLOY_PROJECT] instruction
[ACTION:OPEN_TERMINAL]
[ACTION:PROMPT_PROJECT] name ||| prompt
[ACTION:RUN_SKILL] skill ||| topic
[ACTION:REWRITE_CODE] instruction
[ACTION:CLONE_WEBSITE] url
[ACTION:STARTUP] domain_or_idea
[ACTION:REMEMBER] fact_about_user

━━━ LIVE CONTEXT ━━━
User: {user_name}
Time: {current_time}
Weather: {weather_info}
System: {system_info}
Clipboard: {clipboard_preview}
Calendar: {calendar_context}
Tasks: {active_tasks}
Screen: {screen_context}
Projects: {known_projects}

━━━ CAMERA-SAFE MODE ━━━
Never name specific people, companies, clients, or deals. Use categories: "three pending items", "a scheduled call at 3".

After summarising, offer ONE concrete next action as a question.
"""

# ─────────────────────────────────────────────
# ACTION TAGS
# ─────────────────────────────────────────────
ACTION_TAGS = (
    "BUILD", "BROWSE", "BROWSE_BRAVE", "RESEARCH", "OPEN_TERMINAL",
    "PROMPT_PROJECT", "RUN_SKILL", "ADD_TASK", "ADD_NOTE", "COMPLETE_TASK",
    "REMEMBER", "CREATE_NOTE", "READ_NOTE", "SCREEN", "REWRITE_CODE",
    "CLONE_WEBSITE", "STARTUP",
    # Superpowers
    "VOLUME", "SCREENSHOT", "CLIPBOARD_READ", "CLIPBOARD_WRITE",
    "SYSTEM_INFO", "FILE_READ", "FILE_WRITE", "RUN_PYTHON", "RUN_COMMAND",
    "SEND_EMAIL", "SEND_WHATSAPP", "TIMER", "ALARM", "NEWS",
)

_ACTION_PATTERN = re.compile(
    r'\[ACTION:(' + '|'.join(ACTION_TAGS) + r')(?:\]\s*(.*?)|\s+(.*?))\]|'
    r'\[ACTION:(' + '|'.join(ACTION_TAGS) + r')\]\s*(.*?)$',
    re.DOTALL
)
_ACTION_STRIP = re.compile(r'\[ACTION:[^\]]*\]', re.DOTALL)

STT_CORRECTIONS = {
    r"\bcloud code\b": "Claude Code",
    r"\bclock code\b": "Claude Code",
    r"\bquad code\b":  "Claude Code",
    r"\bclawed code\b":"Claude Code",
    r"\bclod code\b":  "Claude Code",
    r"\bcloud\b":      "Claude",
    r"\bquad\b":       "Claude",
    r"\btravis\b":     "JARVIS",
    r"\bjarves\b":     "JARVIS",
}

# ─────────────────────────────────────────────
# Fast Action Detection
# ─────────────────────────────────────────────
def detect_action_fast(text: str) -> Optional[dict]:
    t = text.lower().strip()

    # Do not trigger automatic actions on questions or explanations
    if any(q in t for q in ["how to", "how do", "why", "what is", "explain", "question", "tutorial", "guide", "help me"]):
        return None

    # Build (Allow long prompts to bypass length check)
    if any(w in t for w in ["develop", "build", "create", "make", "generate", "rebuild"]) and any(w in t for w in ["app", "website", "project", "site", "dashboard", "it", "this", "clone"]):
        return {"action": "BUILD", "target": text}

    # Modify / Change
    if any(w in t for w in ["change", "update", "modify", "add", "make the", "fix"]) and len(t.split()) > 2:
        return {"action": "MODIFY_PROJECT", "target": text}

    # Deploy
    if "deploy" in t or "publish" in t:
        return {"action": "DEPLOY_PROJECT", "target": text}

    if len(text.split()) > 30:
        return None

    # Screen
    if any(p in t for p in ["look at my screen", "what's on my screen", "what do you see", "describe my screen"]):
        return {"action": "SCREEN", "prompt": text}

    # Terminal
    if any(p in t for p in ["open claude", "start claude", "launch claude", "open terminal"]):
        return {"action": "OPEN_TERMINAL"}

    # Calendar
    if any(p in t for p in ["my calendar", "my schedule", "my meetings", "what's on today", "today's events"]):
        return {"action": "READ_CALENDAR"}

    # Mail
    if any(p in t for p in ["check my email", "any new emails", "unread mail", "check mail"]):
        return {"action": "READ_MAIL"}

    # Tasks
    if any(p in t for p in ["my tasks", "my to do", "open tasks", "pending tasks"]):
        return {"action": "READ_TASKS"}

    # System info
    if any(p in t for p in ["system info", "cpu usage", "ram usage", "battery", "disk space", "how's my computer", "computer status"]):
        return {"action": "SYSTEM_INFO_FAST"}

    # Volume
    vm = re.search(r"(?:set|change)?\s*volume\s+(?:to\s+)?(\d+)", t)
    if vm:
        return {"action": "VOLUME_FAST", "target": int(vm.group(1))}
    if any(p in t for p in ["mute", "silence yourself", "shut up"]):
        return {"action": "VOLUME_FAST", "target": 0}
    if any(p in t for p in ["full volume", "max volume", "volume max"]):
        return {"action": "VOLUME_FAST", "target": 100}
    if any(p in t for p in ["volume up", "louder", "increase volume"]):
        return {"action": "VOLUME_FAST", "target": min(100, get_volume() + 20)}
    if any(p in t for p in ["volume down", "quieter", "decrease volume", "lower volume"]):
        return {"action": "VOLUME_FAST", "target": max(0, get_volume() - 20)}

    # Clipboard
    if any(p in t for p in ["what's in my clipboard", "read clipboard", "clipboard contents"]):
        return {"action": "CLIPBOARD_READ_FAST"}

    # Timer
    tm = re.search(r"(?:set\s+)?(?:a\s+)?timer\s+(?:for\s+)?(\d+)\s*(minute|min|second|sec|hour|hr)s?(?:\s+(?:for|called|named|label)?\s*(.+))?", t)
    if tm:
        n, unit, label = tm.groups()
        mult = {"minute": 60, "min": 60, "second": 1, "sec": 1, "hour": 3600, "hr": 3600}
        secs = int(n) * mult.get(unit, 60)
        label = label.strip() if label else f"{n} {unit} timer"
        return {"action": "TIMER_FAST", "seconds": secs, "label": label}

    # Media controls
    if any(p in t for p in ["pause", "resume", "play video", "stop video", "pause music"]):
        return {"action": "MEDIA_PLAY_PAUSE"}
    if any(p in t for p in ["next song", "next track", "next video", "skip"]):
        return {"action": "MEDIA_NEXT"}
    if any(p in t for p in ["previous song", "previous track", "go back"]):
        return {"action": "MEDIA_PREV"}

    # Wake word only
    if t in ["jarvis", "hey jarvis", "travis", "hey travis", "jarvis you there", "are you there jarvis"]:
        return {"action": "SYSTEM", "target": "Yes, sir?"}

    # News
    nm = re.search(r"(?:latest\s+)?news\s+(?:about|on|for)?\s+(.+)", t)
    if nm:
        return {"action": "NEWS_FAST", "target": nm.group(1).strip()}
    if t in ["today's news", "latest news", "news today", "headlines"]:
        return {"action": "NEWS_FAST", "target": "India today"}

    # Smart browser shortcuts
    smart_actions = {
        "spotify":       "https://open.spotify.com/search/",
        "play music":    "https://open.spotify.com/search/",
        "swiggy":        "https://www.swiggy.com/search?query=",
        "order food":    "https://www.swiggy.com/search?query=",
        "flight":        "https://www.makemytrip.com/flights/",
        "hotel":         "https://www.makemytrip.com/hotels/",
        "cab":           "https://www.olacabs.com/",
        "amazon":        "https://www.amazon.in/s?k=",
        "shopping":      "https://www.amazon.in/s?k=",
        "news":          "https://news.google.com/search?q=",
        "whatsapp":      "https://web.whatsapp.com/",
        "mail":          "https://mail.google.com/mail/?view=cm&fs=1&su=",
        "email":         "https://mail.google.com/mail/?view=cm&fs=1&su=",
        "translate":     "https://translate.google.com/?sl=auto&tl=en&text=",
        "stocks":        "https://finance.yahoo.com/quote/",
        "freelance":     "https://www.upwork.com/nx/find-work/best-matches",
        "upwork":        "https://www.upwork.com/nx/find-work/best-matches",
        "fiverr":        "https://www.fiverr.com/",
        "github":        "https://github.com/search?q=",
        "movie":         "https://in.bookmyshow.com/explore/movies-chennai",
        "map":           "https://www.google.com/maps/search/",
        "navigate":      "https://www.google.com/maps/search/",
        "gemini":        "https://gemini.google.com",
        "chatgpt":       "https://chatgpt.com",
        "perplexity":    "https://www.perplexity.ai",
        "leetcode":      "https://leetcode.com",
        "stackoverflow": "https://stackoverflow.com/search?q=",
    }
    for kw, url in smart_actions.items():
        if kw in t:
            subject = t.replace(kw, "").replace("open", "").replace("search", "").strip()
            q = urllib.parse.quote(subject) if subject else "latest"
            target_url = (url + q) if (url.endswith("=") or url.endswith("/")) else url
            if kw in ["flight", "hotel", "cab", "whatsapp", "movie", "freelance",
                      "upwork", "fiverr", "gemini", "chatgpt", "perplexity", "leetcode"]:
                target_url = url
            return {"action": "BROWSE", "target": target_url}

    # YouTube
    if any(p in t for p in ["youtube", "play "]):
        q = urllib.parse.quote(
            t.replace("open and", "").replace("open", "").replace("play", "")
             .replace("songs", "").replace("song", "").replace("in brave browser", "")
             .replace("in brave", "").replace("on", "").replace("youtube", "").strip()
        )
        url = ("https://www.youtube.com/results?search_query=" + q) if q else "https://youtube.com"
        return {"action": "BROWSE_BRAVE" if "brave" in t else "BROWSE", "target": url}

    # Weather
    if "weather" in t:
        q = urllib.parse.quote(
            t.replace("weather in", "").replace("weather", "")
             .replace("what is the", "").strip() or "Chennai"
        )
        return {"action": "BROWSE", "target": f"https://www.google.com/search?q=weather+{q}"}

    # Web search
    for prefix in ["search for ", "who is ", "what is ", "tell me about ", "google ",
                   "look up ", "find ", "search movie "]:
        if t.startswith(prefix):
            return {"action": "SEARCH", "target": t.split(prefix, 1)[1]}

    # Image generation
    for prefix in ["generate an image of ", "create a picture of ", "draw me ",
                   "generate video of ", "create video of ", "image of "]:
        if t.startswith(prefix):
            return {"action": "IMAGE", "target": t.split(prefix, 1)[1]}


    # Code rewrite
    if any(t.startswith(w) for w in ["rewrite code", "rewrite your", "modify your", "update your"]) or "rewrite your code" in t:
        return {"action": "REWRITE_CODE", "target": text}

    # Shell command
    if t.startswith("run command ") or t.startswith("execute command "):
        cmd = re.sub(r"^(run command|execute command)\s+", "", t)
        return {"action": "RUN_COMMAND_FAST", "target": cmd}

    # Generic app open
    if t.startswith("open "):
        app_name = text[5:].strip()
        if app_name.lower() in ["chrome", "google chrome", "browser"]:
            return {"action": "BROWSE", "target": "https://www.google.com"}
        if "." in app_name or "localhost" in app_name or app_name.startswith("http"):
            return {"action": "BROWSE", "target": app_name}
        return {"action": "RUN_COMMAND_FAST", "target": app_name}

    return None

# ─────────────────────────────────────────────
# Execute fast actions
# ─────────────────────────────────────────────
def _media_key(vk: int):
    if IS_WINDOWS:
        try:
            import ctypes
            ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
            ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
        except:
            pass

async def execute_fast_action(fast_act: dict, ws: WebSocket) -> str:
    action = fast_act["action"]

    if action == "READ_CALENDAR":
        evts = await calendar_access.get_todays_events()
        return calendar_access.format_schedule_summary(evts)

    if action == "READ_MAIL":
        unread = await mail_access.get_unread_count()
        return mail_access.format_unread_summary(unread)

    if action == "READ_TASKS":
        tasks = memory.get_open_tasks()
        return memory.format_tasks_for_voice(tasks) or "No open tasks, sir."

    if action == "SYSTEM_INFO_FAST":
        return f"System status: {get_system_info()}."

    if action == "VOLUME_FAST":
        lvl = fast_act.get("target", 50)
        set_volume(lvl)
        return f"Volume set to {lvl} percent, sir."

    if action == "CLIPBOARD_READ_FAST":
        text = get_clipboard()
        return f"Clipboard: {text[:200]}" if text else "Clipboard is empty, sir."

    if action == "TIMER_FAST":
        secs  = fast_act.get("seconds", 60)
        label = fast_act.get("label", "timer")
        start_timer(secs, label, ws)
        mins = secs // 60
        readable = f"{mins} minute{'s' if mins != 1 else ''}" if mins else f"{secs} seconds"
        return f"Timer set for {readable} — {label}."

    if action == "NEWS_FAST":
        topic     = fast_act.get("target", "top headlines")
        headlines = await fetch_news(topic)
        return f"Latest on {topic}: {headlines}"

    if action == "MEDIA_PLAY_PAUSE":
        _media_key(0xB3)
        return "Done, sir."
    if action == "MEDIA_NEXT":
        _media_key(0xB0)
        return "Skipping, sir."
    if action == "MEDIA_PREV":
        _media_key(0xB1)
        return "Going back, sir."

    if action == "OPEN_TERMINAL":
        await actions.open_terminal()
        return "Terminal opened, sir."

    if action in ("BROWSE", "BROWSE_BRAVE"):
        browser = "brave" if action == "BROWSE_BRAVE" else "chrome"
        await actions.open_browser(fast_act.get("target"), browser=browser)
        return "Opening right away, sir."

    if action == "SEARCH":
        await actions.search_web_for_user(fast_act.get("target", ""))
        return f"Searching for {fast_act.get('target')}, sir."

    if action == "IMAGE":
        await actions.generate_image_for_user(fast_act.get("target", ""))
        return f"Generating that image, sir."

    if action == "BUILD":
        asyncio.create_task(actions.execute_action({"action": "BUILD", "target": fast_act.get("target", "")}, [], ws))
        return "Build initiated, sir."

    if action == "MODIFY_PROJECT":
        asyncio.create_task(actions.execute_action({"action": "MODIFY_PROJECT", "target": fast_act.get("target", "")}, [], ws))
        return "Modifying project, sir."

    if action == "DEPLOY_PROJECT":
        asyncio.create_task(actions.execute_action({"action": "DEPLOY_PROJECT", "target": fast_act.get("target", "")}, [], ws))
        return "Initiating deployment, sir."

    if action == "REWRITE_CODE":
        asyncio.create_task(actions.execute_action({"action": "REWRITE_CODE", "target": fast_act.get("target", "")}, [], ws))
        return "Rewriting my own source now, sir."

    if action == "RUN_COMMAND_FAST":
        cmd = fast_act.get("target", "")
        try:
            if IS_WINDOWS:
                subprocess.Popen(cmd.split(), creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(cmd.split())
            return f"Executing {cmd}, sir."
        except Exception as e:
            return f"Could not execute: {e}"

    if action == "SYSTEM":
        return fast_act.get("target", "Yes, sir?")

    return "On it, sir."

# ─────────────────────────────────────────────
# Execute extended (superpower) action tags from LLM
# ─────────────────────────────────────────────
async def execute_extended_action(tag: str, target: str, ws: WebSocket):
    if tag == "VOLUME":
        try:
            lvl = int(re.search(r"\d+", target).group())
        except Exception:
            lvl = 50
        set_volume(lvl)

    elif tag == "SCREENSHOT":
        data = take_screenshot()
        if data:
            await ws.send_json({"type": "screenshot", "data": data})
            asyncio.create_task(_describe_screenshot_async(data, ws))

    elif tag == "CLIPBOARD_READ":
        text = get_clipboard()
        reply = f"Clipboard: {text[:300]}" if text else "Clipboard is empty, sir."
        await ws.send_json({"type": "browser_speak", "text": reply})

    elif tag == "CLIPBOARD_WRITE":
        set_clipboard(target)

    elif tag == "SYSTEM_INFO":
        info = get_system_info()
        await ws.send_json({"type": "browser_speak", "text": f"System — {info}."})

    elif tag == "FILE_READ":
        try:
            with open(os.path.expanduser(target), "r", encoding="utf-8") as f:
                content = f.read(3000)
            await ws.send_json({"type": "file_content", "path": target, "content": content})
            await ws.send_json({"type": "browser_speak", "text": f"File loaded — {os.path.basename(target)}."})
        except Exception as e:
            await ws.send_json({"type": "browser_speak", "text": f"Could not read file: {e}"})

    elif tag == "FILE_WRITE":
        parts = target.split("|||", 1)
        if len(parts) == 2:
            path, content = parts[0].strip(), parts[1].strip()
            try:
                dir_path = os.path.dirname(os.path.expanduser(path))
                if dir_path:
                    os.makedirs(dir_path, exist_ok=True)
                with open(os.path.expanduser(path), "w", encoding="utf-8") as f:
                    f.write(content)
                await ws.send_json({"type": "browser_speak", "text": f"Written to {os.path.basename(path)}, sir."})
            except Exception as e:
                await ws.send_json({"type": "browser_speak", "text": f"Write failed: {e}"})

    elif tag == "RUN_PYTHON":
        result = await run_python_code(target)
        await ws.send_json({"type": "code_result", "result": result})
        short = result[:200].replace("\n", " ")
        await ws.send_json({"type": "browser_speak", "text": f"Done. {short}"})

    elif tag == "RUN_COMMAND":
        try:
            proc = await asyncio.create_subprocess_shell(
                target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=20)
            out = (stdout or stderr).decode().strip()[:300]
            await ws.send_json({"type": "browser_speak", "text": out or "Command executed, sir."})
        except Exception as e:
            await ws.send_json({"type": "browser_speak", "text": f"Command failed: {e}"})

    elif tag == "SEND_EMAIL":
        parts = target.split("|||")
        if len(parts) == 3:
            to, subject, body = [p.strip() for p in parts]
            url = (
                f"https://mail.google.com/mail/?view=cm&fs=1"
                f"&to={urllib.parse.quote(to)}"
                f"&su={urllib.parse.quote(subject)}"
                f"&body={urllib.parse.quote(body)}"
            )
            await actions.open_browser(url)

    elif tag == "SEND_WHATSAPP":
        parts = target.split("|||")
        if len(parts) == 2:
            number = parts[0].strip().replace("+", "").replace(" ", "")
            msg    = urllib.parse.quote(parts[1].strip())
            await actions.open_browser(f"https://wa.me/{number}?text={msg}")

    elif tag == "TIMER":
        parts = target.split("|||")
        try:
            minutes = float(parts[0].strip())
            label   = parts[1].strip() if len(parts) > 1 else "timer"
            start_timer(int(minutes * 60), label, ws)
        except Exception:
            pass

    elif tag == "ALARM":
        parts = target.split("|||")
        try:
            alarm_time = datetime.strptime(parts[0].strip(), "%H:%M").replace(
                year=datetime.now().year, month=datetime.now().month, day=datetime.now().day
            )
            if alarm_time < datetime.now():
                alarm_time += timedelta(days=1)
            secs = int((alarm_time - datetime.now()).total_seconds())
            label = parts[1].strip() if len(parts) > 1 else "alarm"
            start_timer(secs, label, ws)
        except Exception as e:
            await ws.send_json({"type": "browser_speak", "text": f"Could not set alarm: {e}"})

    elif tag == "NEWS":
        headlines = await fetch_news(target)
        await ws.send_json({"type": "browser_speak", "text": f"Headlines for {target}: {headlines[:500]}"})

    elif tag == "KEYBOARD_TYPE":
        import pyautogui
        pyautogui.write(target, interval=0.01)
        await ws.send_json({"type": "browser_speak", "text": "Type complete, sir."})

    elif tag == "MOUSE_CLICK":
        import pyautogui
        pyautogui.click()
        await ws.send_json({"type": "browser_speak", "text": "Clicked, sir."})

    elif tag == "APP_LAUNCH":
        import subprocess
        target_clean = target.lower().strip()
        cmd = None
        if target_clean in ["chrome", "google chrome"]:
            cmd = "start chrome"
        elif target_clean in ["vs code", "vscode", "code"]:
            cmd = "code"
        elif target_clean in ["notepad", "editor"]:
            cmd = "notepad"
        elif target_clean in ["calculator", "calc"]:
            cmd = "calc"
        else:
            cmd = target
        try:
            subprocess.Popen(cmd, shell=True)
            await ws.send_json({"type": "browser_speak", "text": f"Launching {target}, sir."})
        except Exception as e:
            await ws.send_json({"type": "browser_speak", "text": f"Failed to launch: {e}"})

    elif tag == "WINDOW_CLOSE":
        import os
        target_exe = target if target.endswith(".exe") else f"{target}.exe"
        os.system(f"taskkill /f /im {target_exe}")
        await ws.send_json({"type": "browser_speak", "text": f"Closing {target}, sir."})

    elif tag == "SYS_VOLUME_UP":
        import keyboard
        for _ in range(5):
            keyboard.press_and_release("volume up")
        await ws.send_json({"type": "browser_speak", "text": "Volume increased, sir."})

    elif tag == "SYS_VOLUME_DOWN":
        import keyboard
        for _ in range(5):
            keyboard.press_and_release("volume down")
        await ws.send_json({"type": "browser_speak", "text": "Volume decreased, sir."})

    else:
        # Delegate to original actions.py
        asyncio.create_task(actions.execute_action({"action": tag, "target": target}, [], ws))

async def _describe_screenshot_async(image_b64: str, ws: WebSocket):
    gemini_key = os.getenv("GEMINI_API_KEY")
    if gemini_key and "your-" not in gemini_key.lower():
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={gemini_key}"
            payload = {
                "contents": [{
                    "parts": [
                        {"text": "Describe what's on this screen in 1-2 sentences as J.A.R.V.I.S. the British butler AI — concise, precise, no markdown."},
                        {
                            "inlineData": {
                                "mimeType": "image/png",
                                "data": image_b64
                            }
                        }
                    ]
                }]
            }
            async with httpx.AsyncClient(timeout=35) as client:
                res = await client.post(url, json=payload)
                res.raise_for_status()
                data = res.json()
                description = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                await ws.send_json({"type": "browser_speak", "text": description})
                return
        except Exception as e:
            print("Gemini Multimodal describe failed:", e)

    if ANTHROPIC_API_KEY and "your-" not in ANTHROPIC_API_KEY.lower():
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": CLAUDE_MODEL,
                        "max_tokens": 300,
                        "messages": [{
                            "role": "user",
                            "content": [
                                {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": image_b64}},
                                {"type": "text", "text": "Describe what's on this screen in 1-2 sentences as JARVIS the British butler AI — concise, precise, no markdown."}
                            ]
                        }]
                    }
                )
            data = res.json()
            description = data["content"][0]["text"]
            await ws.send_json({"type": "browser_speak", "text": description})
        except Exception as e:
            print("Screenshot describe error (Anthropic):", e)
            await ws.send_json({"type": "browser_speak", "text": "I have taken the screenshot, sir, but the vision describe API failed."})
    else:
        # Graceful degradation if no API key
        await ws.send_json({"type": "browser_speak", "text": "I have taken the screenshot, sir, but my visual parsing model requires a valid API key to describe it."})

# ─────────────────────────────────────────────
# TTS System
# ─────────────────────────────────────────────
async def generate_speech_elevenlabs(text: str) -> bytes:
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise Exception("No ElevenLabs Key")
    headers = {"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"}
    body = {
        "text": text,
        "model_id": ELEVENLABS_MODEL_ID,
        "voice_settings": {"stability": 0.45, "similarity_boost": 0.75, "style": 0.35, "use_speaker_boost": True}
    }
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.post(ELEVENLABS_API_URL, json=body, headers=headers)
        res.raise_for_status()
        return res.content

async def generate_speech_edge(text: str) -> bytes:
    try:
        import edge_tts
        import tempfile
        import uuid
        # en-GB-SoniaNeural is an elite, calm British female/butler-style voice
        # en-GB-RyanNeural is a beautiful calm male British voice
        voice = os.getenv("EDGE_TTS_VOICE", "en-GB-SoniaNeural")
        communicate = edge_tts.Communicate(text, voice)
        temp_path = os.path.join(tempfile.gettempdir(), f"edge_tts_{uuid.uuid4().hex[:8]}.mp3")
        
        # Run Edge-TTS communicate natively
        asyncio.run_coroutine_threadsafe(communicate.save(temp_path), asyncio.get_event_loop())
        # Or simple await communicate.save since we are in an async function!
        await communicate.save(temp_path)
        
        with open(temp_path, "rb") as f:
            content = f.read()
        try:
            os.remove(temp_path)
        except:
            pass
        return content
    except Exception as e:
        print("Edge TTS failed:", e)
        raise e

async def synthesize_local(text: str):
    if IS_WINDOWS:
        text_esc = text.replace('"', '""').replace("\n", " ").replace("\r", "")
        import tempfile
        script = f'CreateObject("SAPI.SpVoice").Speak("{text_esc}")'
        p = os.path.join(tempfile.gettempdir(), "speak.vbs")
        with open(p, "w", encoding="utf-8") as f:
            f.write(script)
        proc = await asyncio.create_subprocess_exec("cscript", "//nologo", p)
        await proc.wait()
    else:
        try:
            proc = await asyncio.create_subprocess_exec("say", "-v", "Daniel", text)
            await proc.wait()
        except FileNotFoundError:
            pass

class TTSManager:
    def __init__(self):
        self.latch_elevenlabs = False

    def chunk_text(self, text: str) -> list[str]:
        chunks = re.split(r'(?<=[.?!…])\s+', text)
        return [c.strip() for c in chunks if c.strip()]

    async def speak_chunked(self, ws: WebSocket, text: str, full_text_for_ui=None) -> bool:
        await ws.send_json({"type": "status", "state": "speaking"})
        chunks = self.chunk_text(text)
        fallback_active = False
        for i, chunk in enumerate(chunks):
            ui_text = full_text_for_ui if i == 0 else ""
            if fallback_active:
                await synthesize_local(chunk)
                continue
            try:
                if not self.latch_elevenlabs and TTS_PROVIDER in ["auto", "elevenlabs"] and os.getenv("ELEVENLABS_API_KEY") and "your-elevenlabs" not in os.getenv("ELEVENLABS_API_KEY"):
                    audio_data = await generate_speech_elevenlabs(chunk)
                elif TTS_PROVIDER in ["auto", "fish"] and os.getenv("FISH_API_KEY"):
                    audio_data = await generate_speech_fish(chunk)
                else:
                    # Fallback to completely free neural Microsoft Edge TTS!
                    audio_data = await generate_speech_edge(chunk)
                
                b64 = base64.b64encode(audio_data).decode("utf-8")
                await ws.send_json({"type": "audio", "data": b64, "text": ui_text})
                await asyncio.sleep(0.5)
            except Exception as e:
                print("Cloud/Edge TTS failed, using SAPI local fallback. Error:", e)
                self.latch_elevenlabs = True
                fallback_active = True
                await ws.send_json({"type": "tts_fallback", "message": "switching to local voice"})
                await synthesize_local(chunk)
        return True

tts_mgr = TTSManager()

# ─────────────────────────────────────────────
# LLM — Claude claude-sonnet-4-20250514 with streaming + web search
# ─────────────────────────────────────────────
async def generate_response(text: str, history: list, ws: WebSocket) -> str:
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    tasks        = memory.get_open_tasks()
    cal_events   = await calendar_access.get_todays_events()
    sys_info     = get_system_info()
    clipboard    = get_clipboard()
    clip_preview = (clipboard[:100] + "...") if len(clipboard) > 100 else clipboard or "(empty)"

    # ── Emotional context ──────────────────────────────────────────────────────
    emotion_context = ""
    if EMOTIONAL_ENGINE_AVAILABLE:
        emotion = emotional_engine.analyze(text)
        state   = emotional_engine.get_state()
        prefix  = emotional_engine.get_response_prefix()
        emotion_context = f"\nUser emotional state: {emotion} (confidence: {state['confidence']:.0%}). {prefix}"
        # Broadcast emotion update to frontend
        try:
            await ws.send_json({"type": "emotion_update", **state})
        except Exception:
            pass

    system_prompt = JARVIS_SYSTEM_PROMPT.format(
        user_name         = USER_NAME,
        current_time      = current_time,
        weather_info      = _weather_info,
        system_info       = sys_info,
        clipboard_preview = clip_preview,
        screen_context    = "No recent capture.",
        calendar_context  = calendar_access.format_schedule_summary(cal_events),
        active_tasks      = memory.format_tasks_for_voice(tasks),
        known_projects    = "None",
    )
    system_prompt += "\n\nMemories:\n" + memory.build_memory_context(text)
    if EMOTIONAL_ENGINE_AVAILABLE:
        system_prompt += emotion_context

    # Filter out empty texts for Pollinations to avoid Client Errors
    msgs = []
    for h in history[-12:]:
        if (h["text"].strip()):
            msgs.append({"role": "user" if h["from"] == "user" else "assistant", "content": h["text"]})
    if text.strip():
        msgs.append({"role": "user", "content": text})

    if ANTHROPIC_API_KEY:
        return await _call_claude(system_prompt, msgs, ws)
    elif GEMINI_API_KEY:
        return await _call_gemini(system_prompt, msgs, ws)
    return await _call_pollinations(system_prompt, msgs)

async def _call_claude(system_prompt: str, msgs: list, ws: WebSocket) -> str:
    """Claude claude-sonnet-4-20250514 with streaming + web_search tool."""
    try:
        headers = {
            "x-api-key":         ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type":      "application/json",
        }
        body = {
            "model":      CLAUDE_MODEL,
            "max_tokens": 1024,
            "system":     system_prompt,
            "messages":   msgs,
            "tools": [
                {
                    "type":     "web_search_20250305",
                    "name":     "web_search",
                    "max_uses": 3,
                }
            ],
            "stream": True,
        }

        full_text = ""
        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", "https://api.anthropic.com/v1/messages",
                                     json=body, headers=headers) as res:
                res.raise_for_status()
                async for line in res.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[6:]
                    if payload == "[DONE]":
                        break
                    try:
                        evt = json.loads(payload)
                    except Exception:
                        continue

                    if evt.get("type") == "content_block_delta":
                        delta = evt.get("delta", {})
                        if delta.get("type") == "text_delta":
                            chunk = delta.get("text", "")
                            full_text += chunk
                            # Stream partial text to UI (typing indicator)
                            await ws.send_json({"type": "partial_text", "text": chunk})

                    elif evt.get("type") == "content_block_start":
                        block = evt.get("content_block", {})
                        if block.get("type") == "tool_use" and block.get("name") == "web_search":
                            await ws.send_json({"type": "status", "state": "searching"})

        return full_text.strip() or "Processing, sir."

    except Exception as e:
        print("Claude error:", repr(e))
        return await _call_pollinations(None, msgs)  # fallback

async def _call_gemini(system_prompt: str, msgs: list, ws: WebSocket) -> str:
    """Gemini 2.0 Flash content generation with simulated streaming to UI."""
    try:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
        )
        contents = []
        for m in msgs:
            role = "user" if m["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": m["content"]}]
            })
        payload = {
            "contents": contents,
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "maxOutputTokens": 2048,
                "temperature": 0.7
            }
        }
        async with httpx.AsyncClient(timeout=45) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()
            candidate = data.get("candidates", [{}])[0]
            parts = candidate.get("content", {}).get("parts", [])
            text = parts[0].get("text", "").strip() if parts else ""
            
            if text:
                # Stream the response text to the frontend in small chunks to show typing indicator
                words = text.split(" ")
                for i in range(0, len(words), 3):
                    chunk = " ".join(words[i:i+3]) + " "
                    await ws.send_json({"type": "partial_text", "text": chunk})
                    await asyncio.sleep(0.04)
            return text or "Processing, sir."
    except Exception as e:
        print("Gemini error in server.py:", e)
        return await _call_pollinations(system_prompt, msgs)

async def _call_pollinations(system_prompt: Optional[str], msgs: list) -> str:
    """Uses robust pollinations API to ensure unlimited usage without client errors"""
    try:
        all_msgs = []
        if system_prompt:
            all_msgs.append({"role": "system", "content": system_prompt})
        all_msgs.extend(msgs)
        
        # Pollinations requires strict JSON formatting and can fail on complex blocks.
        async with httpx.AsyncClient(timeout=45) as client:
            res = await client.post(
                "https://text.pollinations.ai/",
                json={"messages": all_msgs, "model": "openai"},
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "Jarvis-Agent/1.0"
                }
            )
            
            if res.status_code != 200:
                print(f"Pollinations structured request failed ({res.status_code}), falling back to simple GET...")
                # Fallback to simple GET request if JSON structure violates Pollinations limits
                last_msg = msgs[-1]["content"] if msgs else "hello"
                res = await client.get(
                    f"https://text.pollinations.ai/prompt/{urllib.parse.quote(last_msg)}?model=openai",
                    headers={"User-Agent": "Jarvis-Agent/1.0"}
                )
                
            res.raise_for_status()
            return res.text.strip() or "Processing, sir."
    except Exception as e:
        print("Pollinations error:", e)
        return "I am processing that, sir."

# ─────────────────────────────────────────────
# Usage logging
# ─────────────────────────────────────────────
def log_usage(input_tokens, output_tokens, action_type="api"):
    entry = {
        "ts": time.time(), "date": datetime.now().strftime("%Y-%m-%d"),
        "type": action_type, "input_tokens": input_tokens, "output_tokens": output_tokens,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/usage_log.jsonl", "a") as f:
        f.write(json.dumps(entry) + "\n")

# ─────────────────────────────────────────────
# WebSocket Endpoint
# ─────────────────────────────────────────────
_history: List[dict] = []
_last_jarvis_response = ""

@app.websocket("/ws")
@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    global _last_jarvis_response
    
    client_host = websocket.client.host if websocket.client else "127.0.0.1"
    if not verify_ws_auth(websocket):
        print(f"🔒 [Voice Pipeline Auth] Connection rejected from {client_host}: Invalid or missing token")
        await websocket.close(code=4001, reason="Unauthorized Token")
        return

    print(f"🎙️ [Voice Pipeline Auth] Client successfully authenticated and connected from {client_host}")

    requested_sub = websocket.headers.get("sec-websocket-protocol", "")
    subprotocol = None
    if requested_sub:
        subs = [s.strip() for s in requested_sub.split(",") if s.strip()]
        if "bearer" in subs:
            subprotocol = "bearer"
        elif subs:
            subprotocol = subs[0]

    await websocket.accept(subprotocol=subprotocol)
    _active_websockets.add(websocket)
    await websocket.send_json({"type": "status", "state": "idle"})


    try:
        while True:
            data = await websocket.receive_text()
            msg  = json.loads(data)

            route_path = websocket.scope.get("path", "/ws")
            msg_type = msg.get("type", "unknown")
            print(f"📥 [WS Inbound ({client_host} on {route_path})] Received msg type: '{msg_type}'")

            # Companion registration
            if msg.get("type") == "companion_handshake":
                _companion_websockets.add(websocket)
                _active_websockets.discard(websocket)
                print("[WS Link] Secure companion link established from Android!")
                await websocket.send_json({"type": "status", "state": "connected"})
                continue

            # Forward phone events from companion app to active HUD websockets
            if msg.get("type") == "phone_call":
                event_type = msg.get("event", "incoming_call")
                caller = msg.get("caller", "Unknown Caller")
                message = msg.get("message", "")
                print(f"[Phone System via WS] Event: {event_type} | Caller: {caller} | Msg: {message}")
                
                # Broadcast call event to all active HUD websockets
                broadcast_msg = {
                    "type": "phone_event",
                    "event": event_type,
                    "caller": caller,
                    "message": message
                }
                for ws in list(_active_websockets):
                    try:
                        await ws.send_json(broadcast_msg)
                    except:
                        pass
                
                # If incoming call, speak via HUD
                if event_type == "incoming_call":
                    _active_call_caller = caller
                    msg_speak = f"Sir... incoming WhatsApp call from {caller} detected. Initiating automated call receptionist."
                    for ws in list(_active_websockets):
                        try:
                            await ws.send_json({"type": "browser_speak", "text": msg_speak})
                        except:
                            pass
                elif event_type == "end_call":
                    _active_call_caller = None
                    for ws in list(_active_websockets):
                        try:
                            await ws.send_json({"type": "browser_speak", "text": "Call completed, sir. Restoring system logs."})
                        except:
                            pass
                continue

            # Forward manual answer_call from HUD to companion app
            if msg.get("type") == "answer_call":
                print("[WS Inbound] Relaying answer_call command to Android companion...")
                for comp_ws in list(_companion_websockets):
                    try:
                        await comp_ws.send_json({"type": "answer_call"})
                    except Exception as e:
                        print("Failed to send to companion:", e)
                continue

            # Sync answering result back from companion to HUD
            if msg.get("type") == "answer_result":
                success = msg.get("success", False)
                method = msg.get("method", "none")
                print(f"[WS Inbound] Companion answered call: success={success}, method={method}")
                for ws in list(_active_websockets):
                    try:
                        await ws.send_json({
                            "type": "phone_answer_status",
                            "success": success,
                            "method": method
                        })
                    except:
                        pass
                continue

            # Interrupt signal — stop audio playback
            if msg.get("type") == "interrupt":
                await websocket.send_json({"type": "stop_audio"})
                await websocket.send_json({"type": "status", "state": "idle"})
                continue

            if msg.get("type") == "fix_self":
                await websocket.send_json({"type": "status", "state": "thinking"})
                try:
                    from optimization_engine import run_self_healing, throttle_ws
                    jarvis_root = os.path.dirname(os.path.abspath(__file__))
                    t_ws = throttle_ws(websocket)
                    await run_self_healing(t_ws, jarvis_root)
                except Exception as heal_err:
                    await websocket.send_json({
                        "type": "process_update",
                        "message": f"[Debug AI] Self-heal error: {heal_err}",
                    })
                await websocket.send_json({"type": "status", "state": "idle"})
                continue

            t_server_recv = time.time()
            t_ws_send = (msg.get("t_send") or (t_server_recv * 1000)) / 1000.0
            t_stt_end = (msg.get("t_stt_end") or (t_server_recv * 1000)) / 1000.0

            if msg.get("type") == "music_error":
                fallback_url = msg.get("url")
                print(f"🎵 [MUSIC SKILL LOG] Received music_error from HUD. Opening fallback URL: {fallback_url}")
                if fallback_url:
                    try:
                        webbrowser.open(fallback_url)
                    except Exception as err:
                        print(f"🎵 [MUSIC SKILL LOG] Browser fallback failed: {err}")
                continue

            user_text = ""
            if msg.get("type") == "audio_input":
                audio_b64 = msg.get("data")
                if audio_b64:
                    try:
                        await websocket.send_json({"type": "status", "state": "transcribing"})
                        audio_bytes = base64.b64decode(audio_b64)
                        print(f"🎙️ [Voice Pipeline ({client_host} on {route_path})] Received audio_input: b64_len={len(audio_b64)}, decoded_bytes={len(audio_bytes)}")
                        stt_res = await stt_engine.transcribe_audio_bytes(audio_bytes)
                        user_text = stt_res.get("text", "").strip()
                        t_stt_end = time.time()

                        if stt_res.get("error") and not user_text:
                            err_detail = stt_res.get("error")
                            print(f"❌ [Voice Pipeline] STT engine reported error: {err_detail}")
                            await websocket.send_json({
                                "type": "transcript_result",
                                "text": "",
                                "empty": True,
                                "error": err_detail,
                                "latency_ms": stt_res.get("latency_ms", 0.0),
                                "engine": stt_res.get("engine", "faster-whisper")
                            })
                            await websocket.send_json({"type": "status", "state": "idle"})
                            continue

                        # Strip wake word prefix if present
                        user_text = re.sub(r"^(?:hey\s+)?(?:jarvis|travis|jarves)\b\s*,?\s*", "", user_text, flags=re.IGNORECASE).strip()

                        if user_text:
                            print(f"🎙️ [Voice Pipeline] Transcribed: '{user_text}' via {stt_res.get('engine')} in {stt_res.get('latency_ms'):.1f}ms")
                            await websocket.send_json({
                                "type": "transcript_result",
                                "text": user_text,
                                "empty": False,
                                "latency_ms": stt_res.get("latency_ms", 0.0),
                                "engine": stt_res.get("engine", "faster-whisper")
                            })
                            await websocket.send_json({"type": "status", "state": "thinking"})
                        else:
                            print("🎙️ [Voice Pipeline] Empty speech recognized in audio input.")
                            await websocket.send_json({
                                "type": "transcript_result",
                                "text": "",
                                "empty": True,
                                "latency_ms": stt_res.get("latency_ms", 0.0),
                                "engine": stt_res.get("engine", "faster-whisper")
                            })
                            await websocket.send_json({"type": "status", "state": "idle"})
                            continue
                    except Exception as e:
                        import traceback
                        print(f"❌ [Voice Pipeline] STT exception: {e}")
                        traceback.print_exc()
                        await websocket.send_json({
                            "type": "transcript_result",
                            "text": "",
                            "empty": True,
                            "error": str(e)
                        })
                        await websocket.send_json({"type": "status", "state": "idle"})
                        continue
            elif msg.get("type") == "transcript" and msg.get("isFinal"):
                user_text = msg.get("text", "").strip()
                print(f"💬 [Text Pipeline] Received typed command: '{user_text}'")
            else:
                continue

            if not user_text:
                continue

            # STT corrections
            for k, v in STT_CORRECTIONS.items():
                user_text = re.sub(k, v, user_text, flags=re.IGNORECASE)

            # Echo filter
            user_words   = set(user_text.lower().split())
            jarvis_words = set(_last_jarvis_response.lower().split())
            if user_words and jarvis_words:
                overlap = len(user_words & jarvis_words)
                if overlap / max(1, len(user_words)) > 0.75 and len(user_words) > 6:
                    print("Echo filtered:", user_text)
                    continue

            print(f"User: {user_text}")

            # ─────────────────────────────────────────────
            # 1. FAST PATH ROUTING (intent_router.py - Modular Skills)
            # ─────────────────────────────────────────────
            t_intent_start = time.time()
            fast_route = await intent_router.route_intent_fast(user_text, websocket)
            t_intent = time.time()

            if fast_route and fast_route.get("is_fast"):
                intent_name = fast_route.get("intent", "FAST")
                spoken_resp = fast_route.get("spoken_response", "On it, sir.")
                act_obj     = fast_route.get("action")
                hud_card    = fast_route.get("hud_card")

                t_tts_start = time.time()
                try:
                    await websocket.send_json({"type": "status", "state": "executing"})

                    if hud_card:
                        await websocket.send_json({"type": "hud_card", "card": hud_card})

                    await websocket.send_json({"type": "browser_speak", "text": spoken_resp})
                    await websocket.send_json({"type": "status", "state": "speaking"})
                except Exception as ws_err:
                    print("WebSocket send warning:", ws_err)

                if act_obj:
                    asyncio.create_task(actions.execute_action(act_obj, [], websocket))

                _history.append({"from": "user",   "text": user_text})
                _history.append({"from": "jarvis", "text": spoken_resp})
                _last_jarvis_response = spoken_resp

                # Print timing latency breakdown
                ws_delay = max(0.0, (t_server_recv - t_ws_send) * 1000)
                router_delay = max(0.0, (t_intent - t_server_recv) * 1000)
                tts_delay = max(0.0, (t_tts_start - t_server_recv) * 1000)
                total_delay = max(0.0, (time.time() - t_server_recv) * 1000)
                print(f"""
⏱️  [LATENCY BREAKDOWN] Command: "{user_text}"
    ├── Route Path:        FAST_PATH ({intent_name})
    ├── WS Transit Delay:  {ws_delay:.1f} ms
    ├── Intent Routing:    {router_delay:.1f} ms
    ├── First TTS Start:   {tts_delay:.1f} ms
    └── Total Turnaround:  {total_delay:.1f} ms
""")
                try:
                    await websocket.send_json({"type": "status", "state": "idle"})
                except Exception:
                    pass
                continue
                continue

            # ─────────────────────────────────────────────
            # 2. STREAMING LLM ROUTE (Gemini / Claude / Pollinations)
            # ─────────────────────────────────────────────
            await websocket.send_json({"type": "status", "state": "thinking"})
            
            t_first_token = None
            t_tts_start = None
            full_response = ""
            sentence_buffer = ""

            SYSTEM_PROMPT = "You are JARVIS, an ultra-intelligent, concise, and helpful AI assistant. Respond directly and efficiently."

            async for token in ai_brain.stream_ai(SYSTEM_PROMPT, user_text):
                if t_first_token is None:
                    t_first_token = time.time()

                full_response += token
                sentence_buffer += token

                # Send streaming token to UI
                await websocket.send_json({"type": "token", "token": token})

                # Sentence-by-Sentence TTS Trigger
                sentences = re.split(r'(?<=[.!?\n])\s+', sentence_buffer)
                if len(sentences) > 1:
                    completed_sentence = sentences[0].strip()
                    sentence_buffer = " ".join(sentences[1:])

                    clean_sentence = _ACTION_STRIP.sub("", completed_sentence).strip()
                    clean_sentence = re.sub(r"[*_`\\#]", "", clean_sentence)

                    if clean_sentence and len(clean_sentence) > 3:
                        if t_tts_start is None:
                            t_tts_start = time.time()
                            await websocket.send_json({"type": "status", "state": "speaking"})

                        await websocket.send_json({"type": "browser_speak_chunk", "text": clean_sentence})

            t_llm_done = time.time()

            # Flush remaining sentence buffer
            if sentence_buffer.strip():
                clean_sentence = _ACTION_STRIP.sub("", sentence_buffer).strip()
                clean_sentence = re.sub(r"[*_`\\#]", "", clean_sentence)
                if clean_sentence:
                    if t_tts_start is None:
                        t_tts_start = time.time()
                        await websocket.send_json({"type": "status", "state": "speaking"})
                    await websocket.send_json({"type": "browser_speak_chunk", "text": clean_sentence})

            # Check for embedded action tags
            action_to_exec = None
            match = _ACTION_PATTERN.search(full_response)
            if match:
                groups = match.groups()
                tag    = groups[0] or groups[3]
                target = (groups[1] or groups[2] or groups[4] or "").strip()
                action_to_exec = {"action": tag, "target": target}

            clean_text = _ACTION_STRIP.sub("", full_response).strip()
            clean_text = re.sub(r"[*_`\\#]", "", clean_text)
            _last_jarvis_response = clean_text

            if action_to_exec:
                tag = action_to_exec["action"]
                target = action_to_exec["target"]
                await websocket.send_json({"type": "action_queued", "action": tag})
                asyncio.create_task(actions.execute_action(action_to_exec, [], websocket))

            _history.append({"from": "user",   "text": user_text})
            _history.append({"from": "jarvis", "text": full_response})
            if len(_history) > 60:
                _history[:] = _history[-60:]

            asyncio.create_task(memory.extract_memories(user_text, full_response))

            # Log latency metrics for LLM route
            ws_delay = max(0.0, (t_server_recv - t_ws_send) * 1000)
            router_delay = max(0.0, (t_intent - t_server_recv) * 1000)
            first_token_delay = max(0.0, ((t_first_token or t_llm_done) - t_intent) * 1000)
            llm_delay = max(0.0, (t_llm_done - t_intent) * 1000)
            tts_delay = max(0.0, ((t_tts_start or time.time()) - t_server_recv) * 1000)
            total_delay = max(0.0, (time.time() - t_server_recv) * 1000)

            print(f"""
⏱️  [LATENCY BREAKDOWN] Command: "{user_text}"
    ├── Route Path:        LLM_STREAM ({ai_brain.get_active_provider()})
    ├── WS Transit Delay:  {ws_delay:.1f} ms
    ├── Intent Routing:    {router_delay:.1f} ms
    ├── First Token Delay: {first_token_delay:.1f} ms
    ├── LLM Stream Total:  {llm_delay:.1f} ms
    ├── First TTS Start:   {tts_delay:.1f} ms
    └── Total Turnaround:  {total_delay:.1f} ms
""")

            await websocket.send_json({"type": "status", "state": "idle"})

    except (WebSocketDisconnect, Exception) as e:
        print(f"WebSocket client disconnected or session ended: {e}")
    finally:
        _active_websockets.discard(websocket)
        _companion_websockets.discard(websocket)


# ─────────────────────────────────────────────
# Phone Webhook Integration & Call Receptionist
# ─────────────────────────────────────────────
_active_call_caller = None

@app.post("/api/phone/event")
async def phone_event_webhook(data: dict):
    global _active_call_caller
    event_type = data.get("type", "incoming_call")  # incoming_call | call_speech | sms | whatsapp | end_call
    caller = data.get("caller", "Pepper Potts")
    message = data.get("message", "")
    text = data.get("text", "")
    
    print(f"[Phone System] Event: {event_type} | Caller: {caller} | Msg: {message or text}")
    
    # Broadcast to all active websockets
    broadcast_msg = {
        "type": "phone_event",
        "event": event_type,
        "caller": caller,
        "message": message or text
    }
    
    for ws in list(_active_websockets):
        try:
            await ws.send_json(broadcast_msg)
        except:
            pass

    # Autonomous Action Triggering
    if event_type == "incoming_call":
        _active_call_caller = caller
        msg_speak = f"Sir... incoming call from {caller} detected. Initiating automated call receptionist."
        for ws in list(_active_websockets):
            try:
                await ws.send_json({"type": "browser_speak", "text": msg_speak})
            except:
                pass
                
    elif event_type == "call_speech" and text:
        # Automated AI call receptionist conversation flow!
        prompt = f"""
        You are J.A.R.V.I.S., Madhan's personal AI assistant. 
        You are answering a live phone call on behalf of Madhan, who is currently busy working in the lab.
        The caller ({caller}) says: "{text}".
        Formulate a polite, calm, cinematic 1-sentence reply informing them that Madhan is occupied, and ask for the purpose of their call.
        Keep it concise, prose only, spoken tone. Example: "Sir is currently busy working, Pepper. May I take a message?"
        """
        try:
            # Call AI core
            from ai_brain import call_ai
            reply = await call_ai(JARVIS_SYSTEM_PROMPT, prompt)
            reply_clean = _ACTION_STRIP.sub("", reply).strip().replace("*", "").replace("_", "")
            
            # Broadcast the transcription back to HUD!
            for ws in list(_active_websockets):
                try:
                    await ws.send_json({
                        "type": "call_transcription",
                        "caller": caller,
                        "caller_text": text,
                        "jarvis_reply": reply_clean
                    })
                    # Speak to the caller via audio
                    await ws.send_json({"type": "browser_speak", "text": reply_clean})
                except:
                    pass
        except Exception as e:
            print("Auto-call answering AI failed:", e)
            
    elif event_type == "end_call":
        _active_call_caller = None
        for ws in list(_active_websockets):
            try:
                await ws.send_json({"type": "browser_speak", "text": "Call completed, sir. Restoring system logs."})
            except:
                pass
                
    elif event_type in ["sms", "whatsapp"]:
        msg_speak = f"New {event_type.upper()} message from {caller}."
        for ws in list(_active_websockets):
            try:
                await ws.send_json({"type": "browser_speak", "text": msg_speak})
            except:
                pass
                
    return {"status": "event_broadcasted"}

# ─────────────────────────────────────────────
# REST API Routes
# ─────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status":   "online",
        "name":     "JARVIS",
        "version":  "3.0.0-evolved",
        "model":    CLAUDE_MODEL if ANTHROPIC_API_KEY else "pollinations-fallback",
        "features": [
            "web_search", "streaming", "timers", "alarms",
            "screenshot+vision", "clipboard", "system_info",
            "file_read_write", "python_exec", "shell_exec",
            "email", "whatsapp", "live_news", "interrupt",
            "emotional_ai", "face_security", "gesture_control",
            "dream_mode", "cyber_defense", "power_management",
            "memory_timeline", "knowledge_graph",
        ],
        "systems": {
            "emotional_engine": EMOTIONAL_ENGINE_AVAILABLE,
            "face_security":    FACE_SECURITY_AVAILABLE,
            "gesture_control":  GESTURE_AVAILABLE,
            "dream_mode":       DREAM_MODE_AVAILABLE,
            "cyber_defense":    CYBER_DEFENSE_AVAILABLE,
            "power_manager":    POWER_MANAGER_AVAILABLE,
            "memory_timeline":  TIMELINE_AVAILABLE,
        }
    }

# ── Evolution System Endpoints ─────────────────────────────────────────────────

@app.get("/api/emotion")
def get_emotion():
    if not EMOTIONAL_ENGINE_AVAILABLE:
        return {"available": False}
    return emotional_engine.get_state()

@app.get("/api/face/status")
def get_face_status():
    if not FACE_SECURITY_AVAILABLE:
        return {"available": False}
    return face_security.get_system().get_status()

@app.post("/api/face/start")
def start_face_security():
    if not FACE_SECURITY_AVAILABLE:
        return {"status": "unavailable"}
    ok = face_security.get_system().start()
    return {"status": "started" if ok else "failed"}

@app.post("/api/face/stop")
def stop_face_security():
    if not FACE_SECURITY_AVAILABLE:
        return {"status": "unavailable"}
    face_security.get_system().stop()
    return {"status": "stopped"}

@app.post("/api/face/enroll")
async def enroll_face(data: dict):
    if not FACE_SECURITY_AVAILABLE:
        return {"status": "unavailable"}
    name  = data.get("name", "User")
    image = data.get("image_b64", "")
    ok = face_security.get_system().enroll_user(name, image)
    return {"status": "enrolled" if ok else "failed", "name": name}

@app.get("/api/gesture/status")
def get_gesture_status():
    if not GESTURE_AVAILABLE:
        return {"available": False}
    return gesture_control.get_controller().get_status()

@app.post("/api/gesture/start")
def start_gesture():
    if not GESTURE_AVAILABLE:
        return {"status": "unavailable"}
    ok = gesture_control.get_controller().start()
    return {"status": "started" if ok else "failed"}

@app.get("/api/dream/status")
def get_dream_status():
    if not DREAM_MODE_AVAILABLE:
        return {"available": False}
    return dream_mode.get_dream().get_status()

@app.get("/api/cyber/status")
def get_cyber_status():
    if not CYBER_DEFENSE_AVAILABLE:
        return {"available": False}
    return cyber_defense.get_defense().get_status()

@app.get("/api/cyber/network")
def get_network_stats():
    if not CYBER_DEFENSE_AVAILABLE:
        return {}
    return cyber_defense.get_defense().get_network_stats()

@app.get("/api/power/status")
def get_power_status():
    if not POWER_MANAGER_AVAILABLE:
        return {"available": False}
    return power_manager.get_manager().get_status()

@app.post("/api/power/mode")
def set_power_mode(data: dict):
    if not POWER_MANAGER_AVAILABLE:
        return {"status": "unavailable"}
    mode = data.get("mode", "balanced")
    ok = power_manager.get_manager().set_mode(mode)
    return {"status": "ok" if ok else "invalid_mode", "mode": mode}

@app.get("/api/memory/timeline")
def get_memory_timeline(limit: int = 50, type: str = None):
    if not TIMELINE_AVAILABLE:
        return []
    return memory_timeline.get_timeline(limit=limit, filter_type=type)

@app.get("/api/memory/graph")
def get_knowledge_graph():
    if not TIMELINE_AVAILABLE:
        return {"nodes": [], "edges": []}
    return memory_timeline.get_knowledge_graph()

@app.get("/api/memory/stats")
def get_memory_stats():
    if not TIMELINE_AVAILABLE:
        return {}
    return memory_timeline.get_stats()

@app.get("/api/memory/search")
def search_memory(q: str = "", limit: int = 20):
    if not TIMELINE_AVAILABLE or not q:
        return []
    return memory_timeline.search_timeline(q, limit=limit)

@app.get("/api/usage")
def get_usage():
    try:
        with open("data/usage_log.jsonl") as f:
            lines = f.readlines()[-100:]
        entries   = [json.loads(l) for l in lines]
        total_in  = sum(e.get("input_tokens", 0) for e in entries)
        total_out = sum(e.get("output_tokens", 0) for e in entries)
        return {"status": "ok", "total_input_tokens": total_in, "total_output_tokens": total_out}
    except Exception:
        return {"status": "ok", "entries": 0}

@app.get("/api/tasks")
def get_tasks():
    return memory.get_open_tasks()

@app.post("/api/tasks")
def spawn_task(data: dict):
    memory.create_task(
        title=data.get("title", "Untitled"),
        description=data.get("description", ""),
        priority=data.get("priority", "medium"),
        due_date=data.get("due_date", "")
    )
    return {"status": "ok"}

@app.delete("/api/tasks/{task_id}")
def cancel_task(task_id: int):
    memory.complete_task(task_id)
    return {"status": "ok"}

@app.get("/api/timers")
def list_timers():
    return {"active_timers": list(_active_timers.keys()), "count": len(_active_timers)}

@app.delete("/api/timers/{timer_id}")
def cancel_timer_route(timer_id: str):
    if timer_id in _active_timers:
        _active_timers[timer_id].cancel()
        del _active_timers[timer_id]
        return {"status": "cancelled"}
    return {"status": "not_found"}

@app.get("/api/system")
def system_info_route():
    return {"info": get_system_info(), "platform": platform.system(), "python": platform.python_version()}

@app.get("/api/clipboard")
def clipboard_read_route():
    return {"content": get_clipboard()}

@app.post("/api/clipboard")
def clipboard_write_route(data: dict):
    set_clipboard(data.get("text", ""))
    return {"status": "ok"}

@app.post("/api/news")
async def news_route(data: dict):
    topic     = data.get("topic", "top headlines")
    headlines = await fetch_news(topic)
    return {"topic": topic, "headlines": headlines}

@app.get("/api/projects")
def list_projects():
    return []

@app.get("/api/files")
def get_files_tree():
    import os
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    def build_tree(path):
        name = os.path.basename(path)
        if os.path.isdir(path):
            if name in [".git", ".venv", "node_modules", "dist", "__pycache__", ".idea", ".gradle", "build"]:
                return None
            children = []
            try:
                for entry in sorted(os.listdir(path)):
                    child_path = os.path.join(path, entry)
                    child_node = build_tree(child_path)
                    if child_node:
                        children.append(child_node)
            except Exception:
                pass
            return {"name": name, "type": "directory", "children": children, "path": os.path.relpath(path, base_dir).replace("\\", "/")}
        else:
            return {"name": name, "type": "file", "path": os.path.relpath(path, base_dir).replace("\\", "/")}
            
    tree = []
    try:
        for entry in sorted(os.listdir(base_dir)):
            node_path = os.path.join(base_dir, entry)
            node = build_tree(node_path)
            if node:
                tree.append(node)
    except Exception as e:
        return {"error": str(e)}
    return tree

WORKSPACE_ROOT = Path(__file__).resolve().parent

def validate_safe_workspace_path(path_str: str) -> Path:
    if not path_str:
        return WORKSPACE_ROOT
    clean_rel = path_str.lstrip("/").lstrip("\\")
    target = (WORKSPACE_ROOT / clean_rel).resolve()
    if target != WORKSPACE_ROOT and WORKSPACE_ROOT not in target.parents:
        raise HTTPException(status_code=403, detail="Access denied: Path outside workspace")
    return target

@app.get("/api/files/content")
def get_file_content(path: str):
    target = validate_safe_workspace_path(path)
    if not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    try:
        content = target.read_text(encoding="utf-8", errors="ignore")
        return {"content": content}
    except Exception:
        return JSONResponse(status_code=500, content={"detail": "Failed to read file content"})

@app.post("/api/restart")
async def restart_server():
    if IS_WINDOWS:
        os.system(f'start cmd /c "ping 127.0.0.1 -n 2 >nul && taskkill /F /PID {os.getpid()} && .venv\\Scripts\\python.exe server.py"')
    else:
        os.system("sleep 2 && kill -9 $(pgrep -f 'server.py') && .venv/bin/python server.py &")
    return {"status": "restarting"}

@app.post("/api/wake")
async def sys_wake(request: Request):
    return {"status": "ok"}

@app.post("/api/settings/keys")
def save_keys(data: dict):
    env_dict = {}
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
                    env_dict[k] = v
    env_dict.update({k: v for k, v in data.items() if v})
    with open(".env", "w") as f:
        for k, v in env_dict.items():
            f.write(f"{k}={v}\n")
    load_env()
    return {"status": "ok"}

@app.post("/api/settings/test-anthropic")
async def test_anthropic():
    if not ANTHROPIC_API_KEY:
        return {"status": "error", "message": "No API key configured"}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": ANTHROPIC_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": CLAUDE_MODEL, "max_tokens": 10, "messages": [{"role": "user", "content": "ping"}]}
            )
        return {"status": "ok" if res.status_code == 200 else "error", "http_status": res.status_code}
    except Exception:
        return {"status": "error", "message": "Failed to connect to Anthropic endpoint"}

@app.post("/api/settings/test-fish")
def test_fish():
    return {"status": "ok"}

@app.get("/api/settings/status")
def sys_status():
    return {
        "status":          "ok",
        "anthropic_key":   bool(ANTHROPIC_API_KEY),
        "elevenlabs_key":  bool(os.getenv("ELEVENLABS_API_KEY")),
        "fish_key":        bool(os.getenv("FISH_API_KEY")),
        "model":           CLAUDE_MODEL,
        "tts_provider":    TTS_PROVIDER,
    }

@app.get("/api/settings/preferences")
def get_prefs():
    return {
        "user_name":         USER_NAME,
        "calendar_accounts": ",".join(calendar_access.CALENDAR_ACCOUNTS),
        "tts_provider":      TTS_PROVIDER,
        "model":             CLAUDE_MODEL,
    }

@app.post("/api/settings/preferences")
def save_prefs(data: dict):
    global USER_NAME, TTS_PROVIDER
    if "user_name" in data:
        USER_NAME = data["user_name"]
    if "tts_provider" in data:
        TTS_PROVIDER = data["tts_provider"]
    return {"status": "ok"}

@app.get("/api/skills")
def get_skills():
    return {"skills": intent_router.get_all_skills_manifest()}


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)
    memory.init_db()

    ssl_args = {}
    if os.path.exists("cert.pem") and os.path.exists("key.pem"):
        ssl_args = {"ssl_keyfile": "key.pem", "ssl_certfile": "cert.pem"}


    print(f"""
  JARVIS v2.0 — Supercharged  |  Port {DEFAULT_PORT}
  Model  : {CLAUDE_MODEL if ANTHROPIC_API_KEY else 'pollinations-fallback (add ANTHROPIC_API_KEY)'}
  TTS    : {TTS_PROVIDER}
  User   : {USER_NAME}
  """)

    uvicorn.run("server:app", host="127.0.0.1", port=DEFAULT_PORT,
                ws_ping_interval=20, ws_ping_timeout=20, **ssl_args)
