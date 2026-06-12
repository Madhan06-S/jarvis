import os
import re
import json
import uuid
import time
import asyncio
import base64
import platform
import subprocess
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, List

import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ─────────────────────────────────────────────
# .env loader
# ─────────────────────────────────────────────
def load_env():
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    k, v = line.strip().split("=", 1)
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

# Update PATH for launchd / macOS / Homebrew compatibility
os.environ["PATH"] += (
    os.pathsep + os.path.expanduser("~/.local/bin") +
    os.pathsep + "/opt/homebrew/bin" +
    os.pathsep + "/usr/local/bin"
)

IS_MAC     = platform.system() == "Darwin"
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"

# Active Timers store  {id: asyncio.Task}
_active_timers: Dict[str, asyncio.Task] = {}

# ─────────────────────────────────────────────
# Lifespan
# ─────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(refresh_context_daemon())
    yield

app = FastAPI(lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
        app_name = text[5:]
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

    else:
        # Delegate to original actions.py
        asyncio.create_task(actions.execute_action({"action": tag, "target": target}, [], ws))

async def _describe_screenshot_async(image_b64: str, ws: WebSocket):
    if ANTHROPIC_API_KEY:
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
    else:
        # Graceful degradation if no API key
        await ws.send_json({"type": "browser_speak", "text": "I have taken the screenshot, sir, but my visual parsing model requires an API key to describe it."})

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

async def generate_speech_fish(text: str) -> bytes:
    key = os.getenv("FISH_API_KEY")
    if not key:
        raise Exception("No Fish Key")
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    body    = {"text": text, "reference_id": FISH_VOICE_ID, "format": "mp3"}
    async with httpx.AsyncClient(timeout=10) as client:
        res = await client.post(FISH_API_URL, json=body, headers=headers)
        res.raise_for_status()
        return res.content

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
                if not self.latch_elevenlabs and TTS_PROVIDER in ["auto", "elevenlabs"]:
                    audio_data = await generate_speech_elevenlabs(chunk)
                elif TTS_PROVIDER in ["auto", "fish"]:
                    audio_data = await generate_speech_fish(chunk)
                else:
                    raise Exception("No cloud TTS configured")
                b64 = base64.b64encode(audio_data).decode("utf-8")
                await ws.send_json({"type": "audio", "data": b64, "text": ui_text})
                await asyncio.sleep(0.5)
            except Exception:
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

    # Filter out empty texts for Pollinations to avoid Client Errors
    msgs = []
    for h in history[-12:]:
        if (h["text"].strip()):
            msgs.append({"role": "user" if h["from"] == "user" else "assistant", "content": h["text"]})
    if text.strip():
        msgs.append({"role": "user", "content": text})

    if ANTHROPIC_API_KEY:
        return await _call_claude(system_prompt, msgs, ws)
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

@app.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket):
    global _last_jarvis_response
    await websocket.accept()
    await websocket.send_json({"type": "status", "state": "idle"})

    try:
        while True:
            data = await websocket.receive_text()
            msg  = json.loads(data)

            # Interrupt signal — stop audio playback
            if msg.get("type") == "interrupt":
                await websocket.send_json({"type": "stop_audio"})
                await websocket.send_json({"type": "status", "state": "idle"})
                continue

            if msg.get("type") == "fix_self":
                await websocket.send_json({"type": "status", "state": "thinking"})
                await asyncio.sleep(2)
                await websocket.send_json({"type": "status", "state": "idle"})
                continue

            if not (msg.get("type") == "transcript" and msg.get("isFinal")):
                continue

            user_text = msg.get("text", "").strip()
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

            await websocket.send_json({"type": "status", "state": "thinking"})
            print(f"User: {user_text}")

            response_text  = ""
            action_to_exec = None

            fast_act = detect_action_fast(user_text)
            if fast_act:
                response_text = await execute_fast_action(fast_act, websocket)
            else:
                response_text = await generate_response(user_text, _history, websocket)

            # Extract action tag from LLM response
            match = _ACTION_PATTERN.search(response_text)
            if match:
                groups = match.groups()
                tag    = groups[0] or groups[3]
                target = (groups[1] or groups[2] or groups[4] or "").strip()
                action_to_exec = {"action": tag, "target": target}
                response_text  = response_text[:match.start()].strip()

            # Clean for TTS
            clean_text = _ACTION_STRIP.sub("", response_text).strip()
            clean_text = re.sub(r"[*_`\\#]", "", clean_text)

            _last_jarvis_response = clean_text
            print(f"JARVIS: {clean_text.encode('ascii', 'replace').decode('ascii')}")

            await websocket.send_json({"type": "browser_speak", "text": clean_text})

            if action_to_exec:
                tag    = action_to_exec["action"]
                target = action_to_exec["target"]
                await websocket.send_json({"type": "action_queued", "action": tag})

                SUPERPOWER_TAGS = {
                    "VOLUME", "SCREENSHOT", "CLIPBOARD_READ", "CLIPBOARD_WRITE",
                    "SYSTEM_INFO", "FILE_READ", "FILE_WRITE", "RUN_PYTHON",
                    "RUN_COMMAND", "SEND_EMAIL", "SEND_WHATSAPP", "TIMER", "ALARM", "NEWS"
                }
                if tag in SUPERPOWER_TAGS:
                    asyncio.create_task(execute_extended_action(tag, target, websocket))
                else:
                    asyncio.create_task(actions.execute_action(action_to_exec, [], websocket))

            _history.append({"from": "user",   "text": user_text})
            _history.append({"from": "jarvis", "text": response_text})

            # Bound history to last 60 turns
            if len(_history) > 60:
                _history[:] = _history[-60:]

            asyncio.create_task(memory.extract_memories(user_text, response_text))
            await websocket.send_json({"type": "status", "state": "idle"})

    except WebSocketDisconnect:
        print("WebSocket client disconnected")

# ─────────────────────────────────────────────
# REST API Routes
# ─────────────────────────────────────────────
@app.get("/api/health")
def health():
    return {
        "status":   "online",
        "name":     "JARVIS",
        "version":  "2.0.0-supercharged",
        "model":    CLAUDE_MODEL if ANTHROPIC_API_KEY else "pollinations-fallback",
        "features": [
            "web_search", "streaming", "timers", "alarms",
            "screenshot+vision", "clipboard", "system_info",
            "file_read_write", "python_exec", "shell_exec",
            "email", "whatsapp", "live_news", "interrupt"
        ],
    }

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
    memory.add_task(
        data.get("priority", "medium"),
        data.get("title", "Untitled"),
        data.get("description", ""),
        data.get("due_date", "")
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

@app.post("/api/restart")
async def restart_server():
    if IS_WINDOWS:
        os.system(f'start cmd /c "ping 127.0.0.1 -n 2 >nul && taskkill /F /PID {os.getpid()} && python server.py"')
    else:
        os.system("sleep 2 && kill -9 $(pgrep -f 'server.py') && python server.py &")
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
    except Exception as e:
        return {"status": "error", "message": str(e)}

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
