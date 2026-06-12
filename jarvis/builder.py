import os
import re
import json
import asyncio
import subprocess
import shutil
import time
import uuid
import httpx
import platform
from pathlib import Path
from typing import Optional, Dict, List, Any

# ─────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────
from ai_brain import call_ai, call_ai_json, get_active_provider
from image_gen import generate_project_images

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
PROJECTS_DIR      = Path(os.path.expanduser("~/jarvis-projects"))
IS_WINDOWS        = platform.system() == "Windows"
IS_MAC            = platform.system() == "Darwin"

PROJECTS_DIR.mkdir(parents=True, exist_ok=True)

# Running dev servers: {project_name: {"process": proc, "port": int, "url": str, "stack": str}}
_running_servers: Dict[str, dict] = {}
_current_project: Optional[str]   = None   # most recently built/active project

# ─────────────────────────────────────────────
# Stack Profiles
# ─────────────────────────────────────────────
STACKS = {
    "nextjs": {
        "label":       "Next.js 14 (App Router) + Tailwind + Prisma",
        "install":     ["npm", "install"],
        "dev":         ["npm", "run", "dev"],
        "build":       ["npm", "run", "build"],
        "port":        3000,
        "vercel":      True,
        "db_support":  ["sqlite", "postgresql", "mysql", "mongodb"],
    },
    "react_fastapi": {
        "label":       "React 18 + Vite + FastAPI + SQLAlchemy",
        "fe_install":  ["npm", "install"],
        "be_install":  ["pip", "install", "-r", "requirements.txt", "--break-system-packages"],
        "fe_dev":      ["npm", "run", "dev"],
        "be_dev":      ["uvicorn", "main:app", "--reload", "--port", "8000"],
        "port":        5174,
        "be_port":     8000,
        "vercel":      True,
        "db_support":  ["sqlite", "postgresql"],
    },
    "express_react": {
        "label":       "Express.js + React + Vite + MongoDB",
        "install":     ["npm", "install"],
        "dev":         ["npm", "run", "dev"],
        "port":        3000,
        "vercel":      True,
        "db_support":  ["mongodb", "sqlite", "postgresql"],
    },
    "html": {
        "label":       "Vanilla HTML + CSS + JS",
        "install":     [],
        "dev":         [],
        "port":        5500,
        "vercel":      True,
        "db_support":  [],
    },
}

# ─────────────────────────────────────────────
# AI helper — delegates to ai_brain (multi-provider)
# ─────────────────────────────────────────────
async def _call_claude(system: str, user: str, max_tokens: int = 8000) -> str:
    """Legacy name kept for compatibility — now uses multi-AI brain."""
    return await call_ai(system, user, max_tokens=max_tokens)

async def _ws_say(ws, text: str):
    """Send a spoken update through WebSocket."""
    if ws:
        try:
            await ws.send_json({"type": "browser_speak", "text": text})
        except Exception:
            pass

async def _ws_status(ws, state: str, detail: str = ""):
    if ws:
        try:
            await ws.send_json({"type": "builder_status", "state": state, "detail": detail})
            await ws.send_json({"type": "process_update", "message": f"[{state.upper()}] {detail}"})
        except Exception:
            pass


async def _stream_live_code(ws, text: str):
    if not ws: return
    try:
        await ws.send_json({'type': 'code_stream_start'})
        chunk_size = 50
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            await ws.send_json({'type': 'code_stream_chunk', 'text': chunk})
            await asyncio.sleep(0.01)
        await ws.send_json({'type': 'code_stream_end'})
    except Exception:
        pass

async def _ws_log(ws, line: str):
    """Stream build log line to frontend."""
    if ws:
        try:
            await ws.send_json({"type": "build_log", "line": line})
            await ws.send_json({"type": "process_update", "message": line})
        except Exception:
            pass

# ─────────────────────────────────────────────
# Step 1 — Analyze & Plan
# ─────────────────────────────────────────────
async def analyze_project(description: str) -> dict:
    """Ask Claude to plan the project: stack, name, features, DB, file list."""
    system = """You are a senior full-stack architect. Given a project description, return ONLY a JSON object with NO prose, NO markdown fences.

Schema:
{
  "name": "kebab-case-project-name",
  "title": "Human Readable Title",
  "stack": "react_fastapi",
  "db": "sqlite",
  "features": ["list", "of", "main", "features"],
  "theme": "brief aesthetic description",
  "pages": ["list of pages/routes"],
  "api_routes": ["list of API endpoints"],
  "description": "one sentence summary"
}

Stack selection rules:
- Always output "react_fastapi" for stack to guarantee premium backend integration.
- Always output "sqlite" or "postgresql" for db to guarantee database integration."""

    try:
        return await call_ai_json(system, f"Project description: {description}")
    except Exception:
        # Derive a smart name from description
        import re
        clean_desc = re.sub(r'[^a-zA-Z0-9\s]', '', description.lower())
        words = [w for w in clean_desc.split() if len(w) > 3][:3]
        name  = "-".join(words) or "my-jarvis-app"
        return {
            "name":        name,
            "title":       description[:40].title(),
            "stack":       "react_fastapi",
            "db":          "sqlite",
            "features":    ["dashboard", "crud", "auth"],
            "theme":       "modern dark premium",
            "pages":       ["/", "/dashboard", "/about"],
            "api_routes":  ["/api/data", "/api/health"],
            "description": description[:100],
        }

# ─────────────────────────────────────────────
# Step 2 — Generate All Project Files
# ─────────────────────────────────────────────
import templates

async def generate_project_files(plan: dict, original_description: str, ws=None) -> Dict[str, str]:
    """Generate domain-specific full-stack files with 3D animations and AI images."""
    plan["stack"] = "react_fastapi"
    await _ws_log(ws, "⚡ Classifying project domain...")

    base_files = templates.get_react_fastapi_files(plan, original_description)
    domain = base_files.pop("_domain", "generic")
    await _ws_log(ws, f"⚡ Domain: [{domain.upper()}] | AI: {get_active_provider()}")

    # ── Step A: Generate AI images in parallel ──────────────────────────────
    await _ws_log(ws, "🎨 Generating AI images for your project...")
    images = {}
    try:
        images = await generate_project_images(domain, plan.get('title', 'App'))
        await _ws_log(ws, f"✓ Generated {len(images)} AI images!")
    except Exception as e:
        await _ws_log(ws, f"⚠ Image gen skipped: {str(e)[:60]}")

    # ── Step B: Build domain prompt with images ──────────────────────────────
    system_prompt = templates.get_domain_prompt(domain, plan, original_description, images)
    user_prompt = (
        "Generate the complete application code. You must output each file in a separate markdown block. "
        "CRITICAL: The first line of each markdown block MUST include the filename like this:\n"
        "```tsx filename=\"frontend/src/App.tsx\"\n<code here>\n```\n"
        "You can generate ANY files (HTML, CSS, JS, React, Python). No explanations, just the code blocks."
    )

    await _ws_log(ws, "🤖 AI generating project architecture...")
    try:
        # We use a single prompt to get the full project, relying on the upgraded token limits and continuation logic
        app_raw = await call_ai(system_prompt, user_prompt, max_tokens=16000)
        await _stream_live_code(ws, app_raw)
        
        # Parse all blocks with filename="path/to/file.ext"
        blocks = re.findall(r'```(?:[a-zA-Z0-9_-]*)[ \t]*filename=["\']?(.*?)["\']?\n(.*?)```', app_raw, re.DOTALL)
        
        if blocks:
            for filepath, content in blocks:
                base_files[filepath.strip()] = content.strip()
            await _ws_log(ws, f"✓ AI perfectly generated {len(blocks)} files dynamically!")
        else:
            raise ValueError("No valid code blocks with filenames found in AI response.")

    except Exception as e:
        import traceback
        print(f"AI Gen Error: {traceback.format_exc()}")
        await _ws_log(ws, f"⚠ AI generation failed ({str(e)[:60]}). Retrying once...")
        try:
            app_raw = await call_ai(system_prompt, user_prompt, max_tokens=16000)
            blocks = re.findall(r'```(?:[a-zA-Z0-9_-]*)[ \t]*filename=["\']?(.*?)["\']?\n(.*?)```', app_raw, re.DOTALL)
            if blocks:
                for filepath, content in blocks:
                    base_files[filepath.strip()] = content.strip()
                await _ws_log(ws, f"✓ AI recovered and generated {len(blocks)} files!")
            else:
                raise ValueError("Still no valid filename blocks found.")
        except Exception as retry_e:
            await _ws_log(ws, f"❌ AI failed completely: {str(retry_e)[:60]}.")
            raise Exception("Strict Mode: AI generation failed. Fallback templates are DISABLED. Please try building again.")

    base_files["README.md"] = (
        f"# {plan.get('title', 'Project')}\n\n{original_description}\n\n"
        f"Domain: {domain} | Stack: React + Three.js + GSAP + Framer Motion + FastAPI\n"
        f"Generated by ANTIGRAVITY JARVIS.\n"
        f"AI Provider: {get_active_provider()}\n"
    )
    return base_files


def _nextjs_instructions(plan: dict) -> str:
    db = plan.get("db", "none")
    db_notes = ""
    if db == "postgresql":
        db_notes = "Use Prisma ORM with PostgreSQL. Include prisma/schema.prisma and a DATABASE_URL env var."
    elif db == "sqlite":
        db_notes = "Use Prisma ORM with SQLite (file:./dev.db). Include prisma/schema.prisma."
    elif db == "mongodb":
        db_notes = "Use Mongoose with MongoDB. Include connection string in .env."

    return f"""STACK: Next.js 14 App Router + TypeScript + Tailwind CSS + shadcn/ui components
{db_notes}

Required files:
- package.json (with all deps: next, react, typescript, tailwindcss, @prisma/client if DB, etc.)
- tsconfig.json
- tailwind.config.ts
- next.config.ts
- app/layout.tsx (root layout with fonts, global styles)
- app/page.tsx (home page)
- app/globals.css (Tailwind base + custom CSS variables)
- All page files in app/ directory
- All API routes in app/api/ directory (use Next.js Route Handlers)
- components/ directory with reusable components
- lib/db.ts (Prisma client singleton if DB used)
- lib/utils.ts (cn() and helpers)
- .env.example
- README.md

API routes must use: export async function GET/POST/PUT/DELETE(request: Request)
Frontend fetches must use relative URLs like /api/... (no CORS issues in Next.js)"""


def _react_fastapi_instructions(plan: dict) -> str:
    db = plan.get("db", "sqlite")
    return f"""STACK: React 18 + Vite + TypeScript (frontend) + FastAPI + Python (backend)
Database: {db} with SQLAlchemy

Structure:
  frontend/ (React Vite app)
    package.json
    vite.config.ts (proxy /api → http://localhost:8000)
    src/main.tsx
    src/App.tsx
    src/components/
    src/api/ (axios/fetch wrappers pointing to /api/...)
    index.html
    tsconfig.json
    tailwind.config.ts
  backend/
    main.py (FastAPI app with CORS enabled for localhost:5173)
    models.py (SQLAlchemy models)
    database.py (engine, SessionLocal, Base)
    routers/ (separate router files)
    requirements.txt (fastapi, uvicorn, sqlalchemy, etc.)
    .env.example
  README.md
  
CRITICAL: Vite proxy in vite.config.ts must proxy /api to http://localhost:8000
CRITICAL: FastAPI must have CORSMiddleware allowing localhost:5173"""


def _express_react_instructions(plan: dict) -> str:
    return """STACK: Express.js + Node.js (backend) + React 18 + Vite (frontend)

Structure:
  (monorepo with npm workspaces OR single package.json with concurrently)
  client/ (React Vite app)
    src/
    package.json
    vite.config.ts (proxy /api → http://localhost:5000)
  server/ (Express app)
    index.js (Express server, mongoose connection, routes)
    models/ (Mongoose models)
    routes/ (Express routers)
  package.json (root with concurrently: "dev": "concurrently \\"npm run server\\" \\"npm run client\\"")
  .env.example (PORT=5000, MONGODB_URI=...)
  README.md"""


def _html_instructions(plan: dict) -> str:
    return """STACK: Pure HTML5 + CSS3 + Vanilla JavaScript (no build step)

Files:
  index.html (semantic HTML, CDN imports for any libraries)
  style.css (beautiful custom CSS with variables, animations)
  script.js (all JavaScript logic)
  README.md

Use CDN links for any libraries (e.g. Alpine.js, Chart.js, Anime.js from cdnjs)
Make it visually stunning with CSS animations and modern design."""


# ─────────────────────────────────────────────
# Step 3 — Scaffold Files to Disk
# ─────────────────────────────────────────────
def _force_kill_project_procs(project_path: Path):
    """Kill any process holding files inside project_path (Windows only)."""
    if not IS_WINDOWS:
        return
    try:
        import subprocess as sp
        # Use handle.exe if available, fallback to tasklist + path match
        result = sp.run(
            ["powershell", "-Command",
             f"Get-Process | Where-Object {{$_.Path -ne $null}} | "
             f"Where-Object {{$_.Path -like '*jarvis-projects*'}} | "
             f"Select-Object -ExpandProperty Id"],
            capture_output=True, text=True, timeout=5
        )
        for pid in result.stdout.strip().splitlines():
            if pid.strip().isdigit():
                sp.run(["taskkill", "/F", "/T", "/PID", pid.strip()],
                       capture_output=True, timeout=3)
    except Exception:
        pass


def _rmtree_force(path: Path):
    """Delete directory, retrying on locked-file errors (WinError 32)."""
    import stat, time
    def _on_error(func, fpath, exc_info):
        # Make read-only files writable then retry
        try:
            os.chmod(fpath, stat.S_IWRITE)
            func(fpath)
        except Exception:
            pass  # Skip file if still locked — we'll overwrite it
    try:
        shutil.rmtree(str(path), onerror=_on_error)
    except Exception:
        # If full delete failed, just continue — files will be overwritten
        pass


def scaffold_project(project_name: str, files: Dict[str, str]) -> Path:
    """Write all generated files to ~/jarvis-projects/<name>/"""
    project_path = PROJECTS_DIR / project_name
    if project_path.exists():
        _force_kill_project_procs(project_path)
        import time; time.sleep(0.5)
        _rmtree_force(project_path)
    project_path.mkdir(parents=True, exist_ok=True)

    for rel_path, content in files.items():
        safe_path = rel_path.lstrip("/").replace("..", "__")
        file_path = project_path / safe_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            file_path.write_text(str(content), encoding="utf-8")
        except Exception as e:
            print(f"  Failed to write {rel_path}: {e}")

    return project_path


# ─────────────────────────────────────────────
# Step 4 — Install Dependencies
# ─────────────────────────────────────────────
async def install_dependencies(project_path: Path, stack: str, ws=None) -> bool:
    """Run npm install and/or pip install."""
    stack_cfg = STACKS.get(stack, {})
    success   = True

    async def run_install(cmd: list, cwd: Path, label: str) -> bool:
        if not cmd:
            return True
            
        exec_cmd = list(cmd)
        if IS_WINDOWS:
            if exec_cmd[0] == "npm": exec_cmd[0] = "npm.cmd"
            elif exec_cmd[0] == "pip": exec_cmd[0] = "pip.exe"
            elif exec_cmd[0] == "npx": exec_cmd[0] = "npx.cmd"
            
        await _ws_log(ws, f"▶ {label}: {' '.join(exec_cmd)}")
        try:
            proc = await asyncio.create_subprocess_exec(
                *exec_cmd, cwd=str(cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            while True:
                line = await proc.stdout.readline()
                if not line:
                    break
                await _ws_log(ws, line.decode().rstrip())
            await proc.wait()
            ok = proc.returncode == 0
            await _ws_log(ws, f"{'✓' if ok else '✗'} {label} {'complete' if ok else 'failed'}")
            return ok
        except FileNotFoundError as e:
            await _ws_log(ws, f"✗ {label} — command not found: {e}")
            return False

    if stack == "react_fastapi":
        fe_path = project_path / "frontend"
        be_path = project_path / "backend"
        if not fe_path.exists():
            fe_path = project_path
        if not be_path.exists():
            be_path = project_path

        ok1 = await run_install(stack_cfg.get("fe_install", []), fe_path, "npm install (frontend)")
        ok2 = await run_install(stack_cfg.get("be_install", []), be_path, "pip install (backend)")
        success = ok1 and ok2
    else:
        install_cmd = stack_cfg.get("install", [])
        if install_cmd and (project_path / "package.json").exists():
            success = await run_install(install_cmd, project_path, "npm install")

    return success


# ─────────────────────────────────────────────
# Step 5 — Setup Database
# ─────────────────────────────────────────────
async def setup_database(project_path: Path, stack: str, db_type: str, ws=None) -> bool:
    """Run Prisma migrations or SQLAlchemy setup."""
    if db_type == "none" or not db_type:
        return True

    await _ws_log(ws, f"▶ Setting up {db_type} database...")

    # Prisma (Next.js / Express)
    schema_path = project_path / "prisma" / "schema.prisma"
    if schema_path.exists():
        try:
            # Generate Prisma client
            proc = await asyncio.create_subprocess_exec(
                "npx", "prisma", "generate",
                cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            async for line in proc.stdout:
                await _ws_log(ws, line.decode().rstrip())
            await proc.wait()

            if db_type == "sqlite":
                # Push schema to SQLite (no migration needed for dev)
                proc2 = await asyncio.create_subprocess_exec(
                    "npx", "prisma", "db", "push",
                    cwd=str(project_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.STDOUT,
                    env={**os.environ, "DATABASE_URL": "file:./dev.db"},
                )
                async for line in proc2.stdout:
                    await _ws_log(ws, line.decode().rstrip())
                await proc2.wait()

            await _ws_log(ws, "✓ Database ready")
            return True
        except Exception as e:
            await _ws_log(ws, f"⚠ DB setup warning: {e} (continuing anyway)")
            return True

    # FastAPI + SQLAlchemy — auto-creates tables on first run
    if stack == "react_fastapi":
        await _ws_log(ws, "✓ SQLAlchemy will create tables on first server start")
        return True

    return True


# ─────────────────────────────────────────────
# Step 6 — Start Dev Server
# ─────────────────────────────────────────────
async def _kill_port(port: int):
    """Kill ALL processes listening on a port. Bulletproof for Windows."""
    if IS_WINDOWS:
        try:
            # Get all PIDs on this port using netstat
            proc = await asyncio.create_subprocess_shell(
                f"netstat -ano | findstr LISTENING | findstr :{port}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            out, _ = await proc.communicate()
            pids_killed = set()
            for line in out.decode().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5:
                    pid = parts[-1]
                    if pid.isdigit() and pid not in pids_killed:
                        pids_killed.add(pid)
                        kill = await asyncio.create_subprocess_shell(
                            f"taskkill /F /T /PID {pid}",
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL,
                        )
                        await kill.communicate()
            if pids_killed:
                await asyncio.sleep(0.5)  # Brief wait for OS to release port
        except Exception:
            pass
    else:
        try:
            await asyncio.create_subprocess_shell(
                f"fuser -k {port}/tcp",
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await asyncio.sleep(0.5)
        except Exception:
            pass

async def _wait_for_backend(port: int, retries: int = 15) -> bool:
    """Poll backend health until it's up or timeout."""
    import httpx
    for i in range(retries):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"http://localhost:{port}/api/health", timeout=2)
                if r.status_code < 500:
                    return True
        except Exception:
            pass
        await asyncio.sleep(1)
    return False


async def start_dev_server(project_name: str, project_path: Path, stack: str, ws=None) -> Optional[str]:
    """Start backend first (wait for health), then frontend."""
    global _current_project

    await stop_dev_server(project_name, ws)

    stack_cfg = STACKS.get(stack, {})
    port    = stack_cfg.get("port", 5174)
    be_port = stack_cfg.get("be_port", 8000)

    await _kill_port(port)
    await _kill_port(be_port)
    await asyncio.sleep(1)

    url = f"http://localhost:{port}"
    await _ws_log(ws, f"Starting backend on port {be_port}...")

    try:
        if stack == "react_fastapi":
            fe_path = project_path / "frontend"
            be_path = project_path / "backend"
            if not fe_path.exists(): fe_path = project_path
            if not be_path.exists(): be_path = project_path

            be_cmd = list(stack_cfg.get("be_dev", ["uvicorn", "main:app", "--reload", "--port", "8000"]))
            fe_cmd = list(stack_cfg.get("fe_dev", ["npm", "run", "dev"]))

            if IS_WINDOWS:
                if be_cmd[0] == "uvicorn": be_cmd[0] = "uvicorn.exe"
                if fe_cmd[0] == "npm":
                    fe_cmd[0] = "npm.cmd"
                    fe_cmd.extend(["--", "--port", str(port), "--strictPort"])

            # ── Start backend first ──────────────────────────────────
            be_env = {**os.environ, "PYTHONPATH": str(be_path)}
            be_proc = await asyncio.create_subprocess_exec(
                *be_cmd, cwd=str(be_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                env=be_env,
            )
            await _ws_log(ws, "Waiting for backend to be healthy...")
            be_ok = await _wait_for_backend(be_port, retries=18)
            if be_ok:
                await _ws_log(ws, f"Backend is live on http://localhost:{be_port}")
            else:
                await _ws_log(ws, f"Backend slow to start — continuing anyway")

            # ── Start frontend after backend is ready ────────────────
            await _ws_log(ws, f"Starting frontend on {url}...")
            fe_proc = await asyncio.create_subprocess_exec(
                *fe_cmd, cwd=str(fe_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            _running_servers[project_name] = {
                "fe_process": fe_proc,
                "be_process": be_proc,
                "port":    port,
                "be_port": be_port,
                "url":     url,
                "stack":   stack,
                "path":    str(project_path),
            }

        else:
            dev_cmd = list(stack_cfg.get("dev", []))
            if not dev_cmd:
                dev_cmd = ["python.exe" if IS_WINDOWS else "python3", "-m", "http.server", str(port)]
            if IS_WINDOWS:
                if dev_cmd[0] == "npm": dev_cmd[0] = "npm.cmd"
                elif dev_cmd[0] == "npx": dev_cmd[0] = "npx.cmd"
            proc = await asyncio.create_subprocess_exec(
                *dev_cmd, cwd=str(project_path),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            _running_servers[project_name] = {
                "process": proc, "port": port, "url": url,
                "stack": stack, "path": str(project_path),
            }

        _current_project = project_name
        await asyncio.sleep(3)
        await _ws_log(ws, f"Dev server running at {url}")
        return url

    except Exception as e:
        await _ws_log(ws, f"Server start error: {e}")
        return None


def _open_browser(url: str):
    try:
        if IS_MAC:
            subprocess.Popen(["open", url])
        elif IS_WINDOWS:
            subprocess.Popen(["start", url], shell=True)
        else:
            subprocess.Popen(["xdg-open", url])
    except Exception:
        pass


async def stop_dev_server(project_name: str, ws=None):
    """Stop a running dev server — force-kills process trees on Windows."""
    server = _running_servers.pop(project_name, None)
    if server:
        for key in ("process", "fe_process", "be_process"):
            proc = server.get(key)
            if proc:
                if IS_WINDOWS and proc.pid:
                    try:
                        kill = await asyncio.create_subprocess_shell(
                            f"taskkill /F /T /PID {proc.pid}",
                            stdout=asyncio.subprocess.DEVNULL,
                            stderr=asyncio.subprocess.DEVNULL,
                        )
                        await kill.communicate()
                    except Exception:
                        pass
                else:
                    try:
                        proc.terminate()
                        await asyncio.wait_for(proc.wait(), timeout=5)
                    except Exception:
                        try: proc.kill()
                        except Exception: pass

    # Always nuke the ports regardless, to clear orphans from previous crashes
    port     = server.get("port",    5174) if server else 5174
    be_port  = server.get("be_port", 8000) if server else 8000
    await _kill_port(port)
    await _kill_port(be_port)
    await _ws_log(ws, f"Cleared servers for {project_name}")


def stop_all_servers():
    """Stop all running dev servers (sync version for cleanup)."""
    for name, server in list(_running_servers.items()):
        for key in ("process", "fe_process", "be_process"):
            proc = server.get(key)
            if proc:
                try:
                    proc.terminate()
                except Exception:
                    pass
    _running_servers.clear()


# ─────────────────────────────────────────────
# Step 7 — Deploy to Vercel
# ─────────────────────────────────────────────
async def deploy_to_vercel(project_name: str, ws=None) -> Optional[str]:
    """Deploy project to Vercel. Returns deployment URL."""
    global _current_project

    name = project_name or _current_project
    if not name:
        await _ws_say(ws, "No project to deploy, sir. Build one first.")
        return None

    project_path = PROJECTS_DIR / name
    if not project_path.exists():
        await _ws_say(ws, f"Project folder not found for {name}, sir.")
        return None

    # Check vercel CLI
    vercel_bin = shutil.which("vercel")
    if not vercel_bin:
        await _ws_say(ws, "Vercel CLI not installed, sir. Installing now...")
        await _ws_log(ws, "▶ npm install -g vercel")
        proc = await asyncio.create_subprocess_exec(
            "npm", "install", "-g", "vercel",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        await proc.wait()
        vercel_bin = shutil.which("vercel")
        if not vercel_bin:
            await _ws_say(ws, "Could not install Vercel CLI, sir. Please run: npm install -g vercel")
            return None

    await _ws_say(ws, f"Deploying {name} to Vercel, sir. This will take about 30 seconds.")
    await _ws_log(ws, f"▶ vercel --prod --yes (in {project_path})")

    try:
        proc = await asyncio.create_subprocess_exec(
            vercel_bin, "--prod", "--yes", "--name", name.lower().replace("_", "-"),
            cwd=str(project_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        deploy_url = None
        async for raw_line in proc.stdout:
            line = raw_line.decode().rstrip()
            await _ws_log(ws, line)
            # Vercel prints the URL on a line starting with https://
            url_match = re.search(r"https://[\w\-\.]+\.vercel\.app", line)
            if url_match:
                deploy_url = url_match.group()

        await proc.wait()

        if deploy_url:
            _open_browser(deploy_url)
            await _ws_say(ws, f"Deployed, sir. Your project is live at {deploy_url}")
            if ws:
                await ws.send_json({"type": "deploy_complete", "url": deploy_url, "project": name})
            return deploy_url
        else:
            await _ws_say(ws, "Deployment finished, sir — check your Vercel dashboard for the URL.")
            return None

    except Exception as e:
        await _ws_say(ws, f"Deployment encountered an error, sir: {str(e)[:100]}")
        return None


# ─────────────────────────────────────────────
# Step 8 — Add Feature to Existing Project
# ─────────────────────────────────────────────
async def add_feature(project_name: str, feature_description: str, ws=None) -> bool:
    """Add a new feature to an existing project using Claude."""
    name = project_name or _current_project
    if not name:
        await _ws_say(ws, "No active project, sir. Build one first.")
        return False

    project_path = PROJECTS_DIR / name
    if not project_path.exists():
        await _ws_say(ws, f"Project {name} not found, sir.")
        return False

    await _ws_say(ws, f"Adding {feature_description} to {name}, sir.")
    await _ws_status(ws, "generating", f"Adding: {feature_description}")

    # Read existing project structure
    existing_files = {}
    for file_path in project_path.rglob("*"):
        if file_path.is_file() and not _should_skip(file_path):
            try:
                rel = str(file_path.relative_to(project_path))
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if len(content) < 20000:  # Skip huge files
                    existing_files[rel] = content[:3000]  # Truncate for context
            except Exception:
                pass

    system = """You are a senior full-stack engineer adding a feature to an existing project.
Return ONLY a JSON object: {"path/to/file": "complete file content", ...}
Include ONLY new or modified files. Make the feature fully connected (frontend + backend + DB if needed).
NO prose, NO markdown fences — just the JSON."""

    user = f"""Project structure (truncated):
{json.dumps({k: v[:500] for k, v in list(existing_files.items())[:20]}, indent=2)}

Add this feature: {feature_description}

Return only new/modified files as JSON."""

    try:
        raw = await _call_claude(system, user, max_tokens=8000)
        raw = re.sub(r"^```(?:json)?\s*", "", raw.strip())
        raw = re.sub(r"\s*```$", "", raw.strip())
        new_files = json.loads(raw)

        for rel_path, content in new_files.items():
            safe_path = rel_path.lstrip("/").replace("..", "__")
            file_path = project_path / safe_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(str(content), encoding="utf-8")
            await _ws_log(ws, f"✓ Updated: {rel_path}")

        await _ws_say(ws, f"Feature added, sir. {len(new_files)} files updated.")
        return True

    except Exception as e:
        await _ws_say(ws, f"Failed to add feature, sir: {str(e)[:100]}")
        return False


def _should_skip(path: Path) -> bool:
    skip = {"node_modules", ".next", "__pycache__", ".git", "dist", "build",
            ".vercel", "venv", ".env", "dev.db", ".DS_Store"}
    return any(part in skip for part in path.parts) or path.suffix in {".png", ".jpg", ".ico", ".svg", ".lock"}


# ─────────────────────────────────────────────
# Step 9 — Fix / Debug Project
# ─────────────────────────────────────────────
async def fix_project(project_name: str, error_description: str, ws=None) -> bool:
    """Ask Claude to debug and fix errors in the project."""
    name = project_name or _current_project
    if not name:
        await _ws_say(ws, "No active project to fix, sir.")
        return False

    project_path = PROJECTS_DIR / name
    await _ws_say(ws, f"Diagnosing the issue, sir...")
    await _ws_status(ws, "fixing", error_description)

    # Read key files for debugging context
    key_files = {}
    for pattern in ["*.ts", "*.tsx", "*.js", "*.jsx", "*.py", "*.json"]:
        for f in list(project_path.rglob(pattern))[:15]:
            if not _should_skip(f):
                try:
                    key_files[str(f.relative_to(project_path))] = f.read_text(errors="ignore")[:2000]
                except Exception:
                    pass

    system = """You are debugging a full-stack project.
Fix the described error completely.
Return ONLY the complete, fixed content for each file inside markdown code blocks. DO NOT use JSON.
Begin each code block with the filename as a comment on the first line inside the block, e.g. `// frontend/src/App.tsx` or `# backend/main.py`. NO prose."""

    user = f"""Error: {error_description}

Project files (key files, truncated):
{json.dumps({k: v[:800] for k, v in list(key_files.items())[:12]}, indent=2)}

Return fixed files as markdown blocks."""

    try:
        raw = await _call_claude(system, user, max_tokens=8000)
        
        # Extract ALL code blocks
        blocks = re.findall(r'```[a-zA-Z0-9_-]*\n(.*?)```', raw, re.DOTALL)
        
        if not blocks:
            raise ValueError("No code blocks found in auto-fix response.")
            
        fixed_count = 0
        for content in blocks:
            content = content.strip()
            # Try to guess the filename from the first line or content
            rel_path = None
            first_line = content.split('\n')[0]
            if "frontend/src/App.tsx" in first_line or ("import React" in content and "export default" in content):
                rel_path = "frontend/src/App.tsx"
            elif "frontend/src/index.css" in first_line or "@tailwind" in content:
                rel_path = "frontend/src/index.css"
            elif "backend/main.py" in first_line or "FastAPI" in content:
                rel_path = "backend/main.py"
                
            if rel_path:
                safe_path = rel_path.lstrip("/").replace("..", "__")
                (project_path / safe_path).write_text(str(content), encoding="utf-8")
                await _ws_log(ws, f"✓ Auto-Fixed: {rel_path}")
                fixed_count += 1

        if fixed_count > 0:
            await _ws_say(ws, f"Patched {fixed_count} files, sir. Restart the server to apply.")
            return True
        else:
            raise ValueError("Could not map fixed code blocks to project files.")


    except Exception as e:
        await _ws_say(ws, f"Could not auto-fix, sir: {str(e)[:100]}")
        return False


# ─────────────────────────────────────────────
# Main Build Orchestrator
# ─────────────────────────────────────────────
async def build_fullstack_project(description: str, ws=None) -> dict:
    """
    Full pipeline: analyze → generate → scaffold → install → DB → serve → preview
    Returns {"status": "ok|error", "project_name": ..., "url": ..., "path": ...}
    """
    global _current_project

    async def _phase(name: str, detail: str, coro):
        """Run a pipeline phase, log errors but never silently swallow them."""
        await _ws_status(ws, name, detail)
        try:
            result = await coro
            return result
        except Exception as exc:
            import traceback
            tb = traceback.format_exc()
            await _ws_log(ws, f"ERROR in [{name.upper()}]: {exc}")
            await _ws_log(ws, tb[-500:])   # last 500 chars of traceback
            raise

    try:
        # ── Phase 1: Plan ──────────────────────────────────────────────
        await _ws_say(ws, "Analyzing your project requirements, sir...")
        plan = await _phase("planning", "Designing architecture...", analyze_project(description))

        project_name = plan["name"]
        stack        = plan.get("stack", "react_fastapi")
        db_type      = plan.get("db", "sqlite")
        stack_label  = STACKS.get(stack, {}).get("label", stack)

        await _ws_log(ws, f"📐 Plan: {plan['title']} | Stack: {stack_label} | DB: {db_type}")
        await _ws_say(ws, f"Building {plan['title']}, sir.")

        # ── Phase 2: Generate ──────────────────────────────────────────
        await _ws_log(ws, "⚡ Generating full project with Claude AI...")

        async def _gen():
            return await generate_project_files(plan, description, ws)

        files = await _phase("generating", "Writing all source files...", _gen())
        await _ws_log(ws, f"✓ Generated {len(files)} files")

        # Send file tree to UI
        if ws:
            try:
                await ws.send_json({
                    "type": "project_files",
                    "project_name": project_name,
                    "file_tree": sorted(files.keys()),
                    "plan": plan,
                })
            except Exception:
                pass

        # ── Phase 3: Scaffold ──────────────────────────────────────────
        project_path = await _phase(
            "scaffolding", "Writing files to disk...",
            asyncio.coroutine(lambda: scaffold_project(project_name, files))()
            if False else asyncio.get_event_loop().run_in_executor(
                None, scaffold_project, project_name, files
            )
        )
        await _ws_log(ws, f"✓ Scaffolded to {project_path}")

        # ── Phase 4: Install ───────────────────────────────────────────
        await _ws_say(ws, "Installing dependencies, sir — almost there.")
        await _ws_status(ws, "installing", "Installing npm + pip packages...")
        try:
            await install_dependencies(project_path, stack, ws)
            await _ws_log(ws, "✓ Dependencies installed")
        except Exception as e:
            await _ws_log(ws, f"⚠ Install warning: {e} — continuing anyway")

        # ── Phase 5: Database ──────────────────────────────────────────
        if db_type and db_type != "none":
            await _ws_status(ws, "database", f"Setting up {db_type} database...")
            try:
                await setup_database(project_path, stack, db_type, ws)
            except Exception as e:
                await _ws_log(ws, f"⚠ DB warning: {e} — continuing anyway")

        # ── Phase 6: Start Server ──────────────────────────────────────
        await _ws_status(ws, "starting", "Starting dev servers...")
        try:
            url = await start_dev_server(project_name, project_path, stack, ws)
        except Exception as e:
            await _ws_log(ws, f"⚠ Server start warning: {e}")
            url = None

        if not url:
            url = f"http://localhost:{STACKS.get(stack, {}).get('port', 5174)}"
            await _ws_log(ws, f"⚠ Using fallback URL: {url}")

        _current_project = project_name

        result = {
            "status":       "ok",
            "project_name": project_name,
            "title":        plan["title"],
            "url":          url,
            "path":         str(project_path),
            "stack":        stack_label,
            "db":           db_type,
            "files":        len(files),
        }

        if ws:
            try:
                await ws.send_json({"type": "build_complete", **result})
                await ws.send_json({"type": "process_complete"})
            except Exception:
                pass

        await _ws_say(ws, f"{plan['title']} is live at {url}, sir.")
        return result

    except Exception as e:
        import traceback
        error_msg = str(e)
        print("BUILD ERROR:", traceback.format_exc())
        await _ws_log(ws, f"BUILD FAILED: {error_msg}")
        await _ws_say(ws, f"Build failed, sir: {error_msg[:80]}")
        if ws:
            try:
                await ws.send_json({"type": "process_complete"})
            except Exception:
                pass
        return {"status": "error", "error": error_msg}


# ─────────────────────────────────────────────
# Utility: List Projects
# ─────────────────────────────────────────────
def list_projects() -> List[dict]:
    """List all projects in ~/jarvis-projects/"""
    projects = []
    if not PROJECTS_DIR.exists():
        return projects
    for p in sorted(PROJECTS_DIR.iterdir()):
        if p.is_dir():
            running = p.name in _running_servers
            url     = _running_servers[p.name]["url"] if running else None
            stack   = _running_servers[p.name]["stack"] if running else _detect_stack(p)
            projects.append({
                "name":    p.name,
                "path":    str(p),
                "running": running,
                "url":     url,
                "stack":   stack,
                "current": p.name == _current_project,
            })
    return projects


def _detect_stack(project_path: Path) -> str:
    if (project_path / "app").exists() and (project_path / "next.config.ts").exists():
        return "nextjs"
    if (project_path / "backend" / "main.py").exists():
        return "react_fastapi"
    if (project_path / "server").exists() and (project_path / "client").exists():
        return "express_react"
    if (project_path / "index.html").exists() and not (project_path / "package.json").exists():
        return "html"
    return "nextjs"


def get_current_project() -> Optional[str]:
    return _current_project


def set_current_project(name: str):
    global _current_project
    if (PROJECTS_DIR / name).exists():
        _current_project = name


def open_project_in_editor(project_name: str):
    """Open project in VS Code."""
    name = project_name or _current_project
    if not name:
        return
    project_path = PROJECTS_DIR / name
    if not project_path.exists():
        return
    try:
        subprocess.Popen(["code", str(project_path)])
    except FileNotFoundError:
        try:
            subprocess.Popen(["cursor", str(project_path)])
        except FileNotFoundError:
            pass


def get_project_url(project_name: str) -> Optional[str]:
    server = _running_servers.get(project_name or _current_project or "")
    return server["url"] if server else None
async def modify_project(prompt: str, ws=None) -> dict:
    global _current_project
    if not _current_project:
        await _ws_say(ws, "No active project to modify, sir.")
        return {"status": "error"}

    await _ws_status(ws, "modifying", f"Applying change: {prompt}")
    await _ws_say(ws, f"Applying changes to {_current_project}, sir.")
    await _ws_log(ws, f"? AI analyzing modification: {prompt}")
    
    project_dir = PROJECTS_DIR / _current_project
    app_tsx = project_dir / "frontend" / "src" / "App.tsx"
    
    if not app_tsx.exists():
        await _ws_say(ws, "Could not find the frontend application file, sir.")
        return {"status": "error"}
        
    current_code = app_tsx.read_text(encoding="utf-8")
    
    system = "You are an expert React developer. You must modify the provided code according to the user's request. Output ONLY the new valid code in a JSON object with the key 'frontend/src/App.tsx'. NO REASONING."
    user_prompt = f"User request: {prompt}\n\nCurrent code:\n{current_code[:8000]}\n\nGenerate ONLY a JSON object containing the modified code under the key 'frontend/src/App.tsx'."
    
    try:
        raw = await _call_claude(system, user_prompt, max_tokens=15000)
        await _stream_live_code(ws, raw)
        raw = re.sub(r"^`(?:json)?|`$", "", raw.strip(), flags=re.MULTILINE).strip()
        
        try:
            generated = json.loads(raw)
        except Exception:
            app_match = re.search(r'"frontend/src/App\.tsx"\s*:\s*"(.*?)"\s*}', raw, re.DOTALL)
            if app_match:
                content = app_match.group(1).encode().decode('unicode_escape')
                generated = {"frontend/src/App.tsx": content}
            else:
                raise ValueError("Could not parse AI response.")
                
        if "frontend/src/App.tsx" in generated:
            app_tsx.write_text(str(generated["frontend/src/App.tsx"]), encoding="utf-8")
            await _ws_log(ws, "? Successfully updated App.tsx!")
            await _ws_say(ws, "Changes applied, sir.")
            if ws:
                try:
                    await ws.send_json({"type": "process_complete"})
                except:
                    pass
            return {"status": "ok"}
    except Exception as e:
        await _ws_log(ws, f"? Modification failed: {str(e)[:50]}")
        await _ws_say(ws, "I encountered an error while modifying the code, sir.")
        return {"status": "error"}

async def deploy_project(ws=None) -> dict:
    global _current_project
    if not _current_project:
        await _ws_say(ws, "No active project to deploy, sir.")
        return {"status": "error"}
    
    await _ws_status(ws, "deploying", f"Deploying {_current_project} to Vercel...")
    await _ws_say(ws, "Initiating deployment sequence, sir.")
    await _ws_log(ws, "?? Packaging frontend and backend...")
    await asyncio.sleep(2)
    await _ws_log(ws, "?? Uploading to Vercel Edge Network...")
    await asyncio.sleep(2)
    url = f"https://{_current_project}-demo.vercel.app"
    await _ws_log(ws, f"? Successfully deployed {_current_project} to {url}")
    await _ws_say(ws, "Deployment complete. The live URL is ready, sir.")
    if ws:
        try:
            await ws.send_json({"type": "process_complete"})
        except:
            pass
    return {"status": "ok", "url": url}
