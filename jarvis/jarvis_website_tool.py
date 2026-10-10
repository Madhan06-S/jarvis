"""
jarvis_website_tool.py
══════════════════════════════════════════════════════════════════════════════
JARVIS Website Builder — All 4 Errors Fixed
  FIX 1 → Claude as primary AI (was missing key)
  FIX 2 → Exponential backoff on 429 (Gemini rate limit)
  FIX 3 → Unsplash + Stability AI image generation
  FIX 4 → Self-contained HTML output (no local paths → Vercel works)
══════════════════════════════════════════════════════════════════════════════
"""

import os, asyncio, httpx, json, zipfile, base64, time, re
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel
import anthropic

router = APIRouter()

# ──────────────────────────────────────────────────────────────────────────
#  CLIENTS & CONFIG
# ──────────────────────────────────────────────────────────────────────────
ANTHROPIC_KEY   = os.getenv("ANTHROPIC_API_KEY")
GEMINI_KEY      = os.getenv("GEMINI_API_KEY")
UNSPLASH_KEY    = os.getenv("UNSPLASH_ACCESS_KEY")
STABILITY_KEY   = os.getenv("STABILITY_API_KEY")
OUTPUT_DIR      = os.getenv("WEBSITE_OUTPUT_DIR", "./jarvis_projects")
PRIMARY_MODEL   = os.getenv("AI_PRIMARY_MODEL", "claude-opus-4-5")
FALLBACK_MODEL  = os.getenv("AI_FALLBACK_MODEL", "gemini-2.0-flash")
MAX_TOKENS      = int(os.getenv("WEBSITE_MAX_TOKENS", "8000"))

anthropic_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY) if ANTHROPIC_KEY else None


# ──────────────────────────────────────────────────────────────────────────
#  MODELS
# ──────────────────────────────────────────────────────────────────────────
class WebsiteRequest(BaseModel):
    name: str
    description: str
    theme: str
    pages: list[str]
    stack: str = "html"          # "html" | "react" | "fullstack"
    domain: str = ""             # e.g. "shopzone.com"
    language: str = "en"
    currency: str = "INR"

class BuildStatus(BaseModel):
    step: str
    progress: int
    message: str
    file: str = ""


# ══════════════════════════════════════════════════════════════════════════
#  FIX 1 + 2  — AI CALLER WITH CLAUDE PRIMARY, GEMINI FALLBACK + BACKOFF
# ══════════════════════════════════════════════════════════════════════════
async def call_ai(prompt: str, retries: int = 5) -> str:
    """
    Try Claude first. On failure or rate-limit → exponential backoff.
    After max retries → fall back to Gemini with its own backoff.
    Never gives up without trying both providers.
    """
    # ── Claude (primary) ────────────────────────────────────────────────
    if anthropic_client:
        for attempt in range(retries):
            try:
                print(f"[JARVIS/Claude] Attempt {attempt+1}/{retries}")
                msg = anthropic_client.messages.create(
                    model=PRIMARY_MODEL,
                    max_tokens=MAX_TOKENS,
                    messages=[{"role": "user", "content": prompt}]
                )
                return msg.content[0].text
            except anthropic.RateLimitError:
                wait = (2 ** attempt) + 1  # 2s, 5s, 9s, 17s, 33s
                print(f"[JARVIS/Claude] 429 rate limit — waiting {wait}s (attempt {attempt+1})")
                await asyncio.sleep(wait)
            except anthropic.APIStatusError as e:
                print(f"[JARVIS/Claude] API error {e.status_code}: {e.message}")
                if e.status_code >= 500:
                    await asyncio.sleep(3)
                else:
                    break
            except Exception as e:
                print(f"[JARVIS/Claude] Unexpected error: {e}")
                break
        print("[JARVIS/Claude] All retries exhausted — switching to Gemini fallback")
    else:
        print("[JARVIS] ANTHROPIC_API_KEY not set — using Gemini directly")

    # ── Gemini (fallback) with backoff ───────────────────────────────────
    return await call_gemini(prompt, retries=retries)


async def call_gemini(prompt: str, retries: int = 5) -> str:
    if not GEMINI_KEY:
        return "<!-- ERROR: No AI providers configured. Set ANTHROPIC_API_KEY in .env -->"
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{FALLBACK_MODEL}:generateContent?key={GEMINI_KEY}"
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}

    for attempt in range(retries):
        try:
            print(f"[JARVIS/Gemini] Attempt {attempt+1}/{retries}")
            async with httpx.AsyncClient(timeout=90) as client:
                r = await client.post(url, json=payload)

                if r.status_code == 429:
                    wait = (2 ** attempt) * 3  # 3s, 6s, 12s, 24s, 48s
                    print(f"[JARVIS/Gemini] 429 rate limit — waiting {wait}s")
                    await asyncio.sleep(wait)
                    continue

                r.raise_for_status()
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]

        except httpx.HTTPStatusError as e:
            print(f"[JARVIS/Gemini] HTTP {e.response.status_code}")
            await asyncio.sleep(2 ** attempt)
        except Exception as e:
            print(f"[JARVIS/Gemini] Error: {e}")
            await asyncio.sleep(2 ** attempt)

    return "<!-- ERROR: All AI providers failed after all retries -->"


# ══════════════════════════════════════════════════════════════════════════
#  FIX 3  — IMAGE GENERATION (MULTI-PROVIDER WITH FALLBACK)
# ══════════════════════════════════════════════════════════════════════════
async def fetch_images(query: str, count: int = 8) -> list[str]:
    """
    Priority: Stability AI (real AI images) → Unsplash (real photos) → Picsum (free fallback)
    Never returns empty list — always gives usable image URLs.
    """
    # ── Option A: Stability AI (real AI-generated images) ───────────────
    if STABILITY_KEY:
        try:
            ai_images = await generate_stability_images(query, count=min(count, 4))
            if ai_images:
                print(f"[JARVIS/Images] Stability AI: {len(ai_images)} images generated")
                # Fill remainder with Unsplash
                remainder = await fetch_unsplash(query, count - len(ai_images))
                return ai_images + remainder
        except Exception as e:
            print(f"[JARVIS/Images] Stability AI failed: {e}")

    # ── Option B: Unsplash (real photos, free) ───────────────────────────
    if UNSPLASH_KEY:
        try:
            images = await fetch_unsplash(query, count)
            if images:
                print(f"[JARVIS/Images] Unsplash: {len(images)} photos fetched")
                return images
        except Exception as e:
            print(f"[JARVIS/Images] Unsplash failed: {e}")

    # ── Option C: Picsum (always works, no key needed) ───────────────────
    print("[JARVIS/Images] Using Picsum fallback")
    seeds = ["tech", "store", "product", "modern", "style", "city", "food", "nature"]
    return [
        f"https://picsum.photos/seed/{query.replace(' ','')+s}{i}/1200/700"
        for i, s in enumerate(seeds[:count])
    ]


async def generate_stability_images(query: str, count: int = 4) -> list[str]:
    """Generate real AI images via Stability AI and return as data: URIs"""
    url = "https://api.stability.ai/v2beta/stable-image/generate/ultra"
    headers = {"Authorization": f"Bearer {STABILITY_KEY}", "Accept": "image/*"}
    images = []
    for i in range(count):
        prompt_text = f"Professional product photography, {query}, high quality, commercial grade, 4K"
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, data={
                "prompt": prompt_text,
                "output_format": "jpeg",
                "width": 1024,
                "height": 576,
            })
            r.raise_for_status()
            b64 = base64.b64encode(r.content).decode()
            images.append(f"data:image/jpeg;base64,{b64}")
    return images


async def fetch_unsplash(query: str, count: int) -> list[str]:
    url = f"https://api.unsplash.com/search/photos"
    params = {"query": query, "per_page": count, "client_id": UNSPLASH_KEY, "orientation": "landscape"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        results = r.json().get("results", [])
        return [p["urls"]["regular"] for p in results]


# ══════════════════════════════════════════════════════════════════════════
#  FIX 4  — SELF-CONTAINED HTML GENERATOR (no local paths → hosting works)
# ══════════════════════════════════════════════════════════════════════════
def build_page_prompt(page: str, req: WebsiteRequest, images: list[str]) -> str:
    img_urls = "\n".join([f"  Image {i+1}: {url}" for i, url in enumerate(images[:6])])
    currency_symbol = "₹" if req.currency == "INR" else "$"

    return f"""Create a COMPLETE, production-grade, single-file HTML page for the "{page}" page
of "{req.name}" ({req.description}).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DESIGN
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Theme: {req.theme}
Stack: {req.stack}
Currency: {currency_symbol}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REAL IMAGES — use these exact URLs
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{img_urls}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 MANDATORY REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SELF-CONTAINED (critical for hosting):
  - ALL CSS embedded in <style> tags — zero external .css files
  - ALL JavaScript embedded in <script> tags — zero external .js files
  - ALL images use the real URLs above — zero local file paths
  - Google Fonts loaded via CDN: <link href="https://fonts.googleapis.com/...">
  - Icon library via CDN: use Font Awesome CDN link

NAVIGATION:
  - Logo with "{req.name}" brand name (styled, not an image)
  - Search bar with placeholder
  - Cart icon with a JS counter badge (increments on "Add to Cart")
  - User/account icon
  - Mobile hamburger menu (toggle JS built-in)
  - Links to: {", ".join(req.pages)}

PAGE CONTENT for "{page}":
  - Hero section: full-width banner, use Image 1 as background-image
  - At least 6 sections relevant to this page type
  - Product/item cards: real names, realistic {currency_symbol} prices, star ratings, "Add to Cart"
  - Countdown timer if deals/offers section present (pure JS)
  - Testimonials section with 3 reviews
  - Newsletter signup

FOOTER (on every page):
  - 4 columns: Brand info | Quick Links | Categories | Newsletter + Social
  - Social icons (use Font Awesome or Unicode)

CODE QUALITY:
  - Fully responsive: CSS Grid + Flexbox, no media query breakpoints missed
  - Hover effects on all cards (transform: translateY + box-shadow)
  - Smooth scroll behavior
  - Real content — no "Lorem ipsum", no placeholder text
  - Color scheme strictly: {req.theme}

RETURN: Only the complete <!DOCTYPE html> document. No explanation, no markdown code fences."""


def sanitize_output(code: str) -> str:
    """Strip markdown fences and ensure pure HTML"""
    code = re.sub(r"^```[\w]*\n?", "", code, flags=re.MULTILINE)
    code = re.sub(r"\n?```$", "", code, flags=re.MULTILINE)
    code = code.strip()
    if not code.startswith("<!"):
        # Try to find the start of HTML
        idx = code.find("<!DOCTYPE")
        if idx == -1:
            idx = code.find("<html")
        if idx != -1:
            code = code[idx:]
    return code


def verify_self_contained(html: str) -> list[str]:
    """Return list of issues that would break hosting"""
    issues = []
    # Check for local JS references
    local_js = re.findall(r'<script[^>]+src=["\'](?!http)([^"\']+)["\']', html)
    for f in local_js:
        issues.append(f"Local JS reference: {f}")
    # Check for local CSS references
    local_css = re.findall(r'<link[^>]+href=["\'](?!http)([^"\']+\.css)["\']', html)
    for f in local_css:
        issues.append(f"Local CSS reference: {f}")
    # Check for local image paths
    local_imgs = re.findall(r'src=["\'](?!http|data:)([^"\']+\.(jpg|jpeg|png|gif|webp|svg))["\']', html)
    for f, _ in local_imgs:
        issues.append(f"Local image reference: {f}")
    return issues


def get_filename(page: str, stack: str) -> str:
    if stack == "react":
        return f"src/pages/{page}.jsx"
    base = "index" if page.lower() == "home" else page.lower().replace(" ", "_")
    return f"{base}.html"


# ══════════════════════════════════════════════════════════════════════════
#  MAIN ENDPOINT — Generate Full Website
# ══════════════════════════════════════════════════════════════════════════
@router.post("/generate-website")
async def generate_website(req: WebsiteRequest):
    project_dir = Path(OUTPUT_DIR) / req.name.lower().replace(" ", "_")
    project_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"[JARVIS] Building: {req.name}")
    print(f"[JARVIS] Pages: {req.pages}")
    print(f"[JARVIS] Stack: {req.stack}")
    print(f"{'='*60}\n")

    # Step 1: Fetch images once (shared across all pages)
    print("[JARVIS] Step 1/3: Fetching images...")
    images = await fetch_images(f"{req.name} {req.description[:40]}")

    # Step 2: Generate pages sequentially (prevents 429s from parallel calls)
    print(f"[JARVIS] Step 2/3: Generating {len(req.pages)} pages sequentially...")
    generated = {}
    warnings = []

    for i, page in enumerate(req.pages):
        print(f"[JARVIS] Page {i+1}/{len(req.pages)}: {page}")
        prompt = build_page_prompt(page, req, images)

        raw_code = await call_ai(prompt)
        clean_code = sanitize_output(raw_code)

        # Verify it's self-contained (FIX 4)
        issues = verify_self_contained(clean_code)
        if issues:
            warnings.append({"page": page, "issues": issues})
            print(f"[JARVIS] WARNING: {page} has {len(issues)} hosting issues")

        filename = get_filename(page, req.stack)
        filepath = project_dir / filename
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(clean_code, encoding="utf-8")
        generated[filename] = str(filepath)
        print(f"[JARVIS] ✓ {filename} ({len(clean_code):,} chars)")

        # Small pause between pages (prevents rate limits)
        if i < len(req.pages) - 1:
            await asyncio.sleep(1.5)

    # Step 3: Package ZIP
    print("[JARVIS] Step 3/3: Creating ZIP...")
    zip_path = Path(OUTPUT_DIR) / f"{req.name.replace(' ', '_')}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname, fpath in generated.items():
            zf.write(fpath, fname)

    print(f"\n[JARVIS] ✅ DONE — {len(generated)} files → {zip_path}\n")

    return {
        "status": "ok",
        "files": list(generated.keys()),
        "file_count": len(generated),
        "zip": str(zip_path),
        "project_dir": str(project_dir),
        "images_used": images[:6],
        "warnings": warnings,   # hosting issues if any
    }


# ══════════════════════════════════════════════════════════════════════════
#  REAL-TIME WEBSOCKET ENDPOINT (for JARVIS swarm UI live updates)
# ══════════════════════════════════════════════════════════════════════════
@router.websocket("/ws/generate")
async def ws_generate(websocket: WebSocket):
    """
    Real-time website generation with live progress updates to JARVIS UI.
    Connect from frontend: const ws = new WebSocket("ws://localhost:8000/api/website/ws/generate")
    Send: JSON WebsiteRequest
    Receive: JSON BuildStatus updates + final result
    """
    await websocket.accept()
    print("[JARVIS/WS] Client connected")

    try:
        raw = await websocket.receive_text()
        data = json.loads(raw)
        req = WebsiteRequest(**data)

        async def send(step: str, progress: int, message: str, file: str = ""):
            await websocket.send_json({
                "step": step, "progress": progress,
                "message": message, "file": file
            })

        await send("init", 5, f"Initializing build for {req.name}...")

        project_dir = Path(OUTPUT_DIR) / req.name.lower().replace(" ", "_")
        project_dir.mkdir(parents=True, exist_ok=True)

        # Fetch images
        await send("images", 10, "Fetching real images...")
        images = await fetch_images(f"{req.name} {req.description[:40]}")
        await send("images", 20, f"Got {len(images)} real images")

        # Generate pages
        generated = {}
        total_pages = len(req.pages)
        for i, page in enumerate(req.pages):
            pct_start = 20 + int((i / total_pages) * 65)
            pct_end   = 20 + int(((i+1) / total_pages) * 65)

            await send("generating", pct_start, f"Writing {page} page...", get_filename(page, req.stack))
            prompt = build_page_prompt(page, req, images)
            raw_code = await call_ai(prompt)
            clean_code = sanitize_output(raw_code)

            filename = get_filename(page, req.stack)
            filepath = project_dir / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            filepath.write_text(clean_code, encoding="utf-8")
            generated[filename] = str(filepath)

            await send("done", pct_end, f"✓ {filename}", filename)
            if i < total_pages - 1:
                await asyncio.sleep(1.5)

        # ZIP
        await send("packaging", 90, "Creating ZIP package...")
        zip_path = Path(OUTPUT_DIR) / f"{req.name.replace(' ', '_')}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname, fpath in generated.items():
                zf.write(fpath, fname)

        await send("complete", 100, "Website ready!", str(zip_path))
        await websocket.send_json({
            "type": "result",
            "status": "ok",
            "files": list(generated.keys()),
            "zip": str(zip_path),
            "images_used": images[:6],
        })

    except WebSocketDisconnect:
        print("[JARVIS/WS] Client disconnected")
    except Exception as e:
        print(f"[JARVIS/WS] Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


# ══════════════════════════════════════════════════════════════════════════
#  DOWNLOAD ZIP ENDPOINT
# ══════════════════════════════════════════════════════════════════════════
@router.get("/download/{project_name}")
async def download_zip(project_name: str):
    zip_path = Path(OUTPUT_DIR) / f"{project_name}.zip"
    if not zip_path.exists():
        return {"error": f"{project_name}.zip not found. Generate it first."}
    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        filename=f"{project_name}.zip"
    )
