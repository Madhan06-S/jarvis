"""
ANTIGRAVITY JARVIS — Multi-AI Brain
Supports: OpenAI GPT-4o, Google Gemini, Anthropic Claude, Pollinations (free fallback)
"""
import os
import re
import json
import asyncio
import httpx
from typing import Optional

# ── Manual .env Loader (Bulletproof & Filter Placeholders) ─────────────────
def _load_env():
    for path in [".env", "../.env", "d:/ironnn/jarvis/.env"]:
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" in line:
                            k, v = line.split("=", 1)
                            k = k.strip()
                            v = v.strip().strip('"').strip("'")
                            if v and "your-" not in v.lower():
                                os.environ[k] = v
            except Exception:
                pass

_load_env()

OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Explicitly clear placeholders from system environment variables
if ANTHROPIC_API_KEY and ("your-" in ANTHROPIC_API_KEY.lower() or ANTHROPIC_API_KEY.startswith("your-")):
    ANTHROPIC_API_KEY = ""
if GEMINI_API_KEY and ("your-" in GEMINI_API_KEY.lower() or GEMINI_API_KEY.startswith("your-")):
    GEMINI_API_KEY = ""
if OPENAI_API_KEY and ("your-" in OPENAI_API_KEY.lower() or OPENAI_API_KEY.startswith("your-")):
    OPENAI_API_KEY = ""

OPENAI_MODEL  = os.getenv("OPENAI_MODEL",  "gpt-4o")
GEMINI_MODEL  = os.getenv("GEMINI_MODEL",  "gemini-2.0-flash")
CLAUDE_MODEL  = os.getenv("CLAUDE_MODEL",  "claude-sonnet-4-20250514")

DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "auto")  # auto | openai | gemini | claude | pollinations

# ─────────────────────────────────────────────
# Continuation deduplication — kills the #1 build error
# ─────────────────────────────────────────────

def _dedup_continuation_restarts(full_text: str) -> str:
    """
    When AI responses are continued after truncation, the AI often restarts
    the entire file from scratch mid-stream, producing patterns like:
      ...some code...
      filename="frontend/src/App.tsx"
      import React, { useState ...
    This function detects these restart boundaries and keeps only the LAST
    complete copy of each file within a code block, eliminating corruption.
    """
    # Pattern: filename="..." appearing mid-text (not at start of a code block)
    restart_pattern = re.compile(
        r'filename=["\']([^"\'\n]+)["\']\s*\n'
    )
    
    # Find all restart points
    matches = list(restart_pattern.finditer(full_text))
    if not matches:
        return full_text
    
    # Group restart points by filename
    restarts_by_file = {}
    for m in matches:
        fname = m.group(1).strip()
        if fname not in restarts_by_file:
            restarts_by_file[fname] = []
        restarts_by_file[fname].append(m)
    
    # For each file that has multiple restart points, we need to keep only
    # the content from the LAST restart to the end (or next different filename)
    if not restarts_by_file:
        return full_text
    
    # Strategy: find all restart markers and cut the text at the LAST one
    # for the most-restarted file
    for fname, file_matches in restarts_by_file.items():
        if len(file_matches) <= 1:
            continue
        
        # Find the opening ``` that contains the LAST restart
        last_restart = file_matches[-1]
        # Look backwards from the restart to find the opening ```
        pre_text = full_text[:last_restart.start()]
        last_fence_pos = pre_text.rfind('```')
        
        if last_fence_pos >= 0:
            # Keep everything before the first restart's code block opening,
            # then the last restart's code block
            first_restart = file_matches[0]
            pre_first = full_text[:first_restart.start()]
            first_fence = pre_first.rfind('```')
            
            if first_fence >= 0:
                # Take: everything before first occurrence + last occurrence onwards
                before = full_text[:first_fence]
                after = full_text[last_fence_pos:]
                full_text = before + after
    
    # Also strip inline filename= that got stuck mid-code (not inside ```)
    # Pattern: code...filename="path"\nimport React → just keep from import
    full_text = re.sub(
        r'(?<=\n)\s*filename=["\'][^"\']+["\']\s*\n(?=import\s)',
        '\n',
        full_text
    )
    
    return full_text


def _clean_ai_output(full_text: str) -> str:
    """Master cleanup for all AI provider outputs."""
    # Remove accidental double backticks from stitched continuations
    full_text = full_text.replace("```\n```", "").replace("``````", "")
    # Remove continuation restart corruption
    full_text = _dedup_continuation_restarts(full_text)
    return full_text


# ─────────────────────────────────────────────
# Individual providers
# ─────────────────────────────────────────────

async def _call_openai(system: str, user: str, max_tokens: int = 8000) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("No OpenAI API key")
    msgs = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user}
    ]
    full_text = ""
    async with httpx.AsyncClient(timeout=120.0) as client:
        while True:
            res = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                         "Content-Type": "application/json"},
                json={
                    "model": OPENAI_MODEL,
                    "max_tokens": max_tokens,
                    "messages": msgs
                }
            )
            res.raise_for_status()
            data = res.json()
            text = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason")
            
            # If this is a continuation, strip leading backticks from the incoming text
            if len(msgs) > 2:
                text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text.lstrip())
                
            full_text += text
            
            if finish_reason == "length" or full_text.count("```") % 2 != 0:
                msgs.append({"role": "assistant", "content": text})
                msgs.append({"role": "user", "content": "Your response was cut off. Please continue EXACTLY where you left off. Do NOT start with backticks, just continue the raw code directly."})
                continue
            else:
                break
                
    return _clean_ai_output(full_text)


async def _call_gemini(system: str, user: str, max_tokens: int = 8000) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("No Gemini API key")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    contents = [{"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]}]
    full_text = ""
    async with httpx.AsyncClient(timeout=120.0) as client:
        while True:
            payload = {
                "contents": contents,
                "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}
            }
            for attempt in range(4):
                res = await client.post(url, json=payload)
                if res.status_code == 429:
                    wait_time = (attempt + 1) * 3
                    print(f"[Gemini] 429 Rate Limit. Waiting {wait_time}s (attempt {attempt+1}/4)...")
                    await asyncio.sleep(wait_time)
                    continue
                res.raise_for_status()
                break
            data = res.json()
            
            candidate = data.get("candidates", [{}])[0]
            parts = candidate.get("content", {}).get("parts", [])
            finish_reason = candidate.get("finishReason")
            
            text = parts[0].get("text", "") if parts else ""
            
            # If this is a continuation, strip leading backticks
            if len(contents) > 1:
                text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text.lstrip())
                
            full_text += text
            
            if finish_reason == "MAX_TOKENS" or full_text.count("```") % 2 != 0:
                contents.append({"role": "model", "parts": [{"text": text}]})
                contents.append({"role": "user", "parts": [{"text": "Your response was cut off. Please continue EXACTLY where you left off. Do NOT start with backticks, just continue the raw code directly."}]})
                continue
            else:
                break
                
    return _clean_ai_output(full_text)


async def _call_claude(system: str, user: str, max_tokens: int = 8000) -> str:
    if not ANTHROPIC_API_KEY:
        raise ValueError("No Anthropic API key")
    msgs = [{"role": "user", "content": user}]
    full_text = ""
    async with httpx.AsyncClient(timeout=180.0) as client:
        while True:
            res = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": msgs
                }
            )
            res.raise_for_status()
            data = res.json()
            text = data["content"][0]["text"]
            
            stop_reason = data.get("stop_reason")
            
            # If this is a continuation, strip leading backticks
            if len(msgs) > 1:
                text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text.lstrip())
                
            full_text += text
            
            if stop_reason == "max_tokens" or full_text.count("```") % 2 != 0:
                msgs.append({"role": "assistant", "content": text})
                msgs.append({"role": "user", "content": "Your response was cut off. Please continue EXACTLY where you left off. Do NOT start with backticks, just continue the raw code directly."})
                continue
            else:
                break
                
    return _clean_ai_output(full_text)


async def _call_pollinations(system: str, user: str, max_tokens: int = 8000) -> str:
    """Free fallback — no API key required."""
    msgs = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user}
    ]
    async with httpx.AsyncClient(timeout=180.0) as client:
        full_text = ""
        while True:
            for attempt in range(3):
                res = await client.post(
                    "https://text.pollinations.ai/",
                    json={"messages": msgs, "model": "openai", "seed": 42}
                )
                if res.status_code == 429 and attempt < 2:
                    import asyncio
                    await asyncio.sleep(2 * (attempt + 1))
                    continue
                res.raise_for_status()
                break
            
            text = res.text.strip()
            # Handle Pollinations occasionally wrapping responses in JSON
            if text.startswith('{') and text.endswith('}'):
                try:
                    data = json.loads(text)
                    if 'choices' in data:
                        text = data['choices'][0]['message']['content']
                    elif 'message' in data:
                        text = data['message'].get('content', '')
                    elif 'content' in data:
                        text = data['content']
                    elif 'reasoning_content' in data and not data.get('content'):
                        text = data.get('reasoning_content', text)
                except Exception:
                    pass
                    
            # If this is a continuation, strip leading backticks
            if len(msgs) > 2:
                text = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", text.lstrip())
                
            full_text += text
            
            # If the number of backticks is odd, the code block is unclosed (truncated)
            if full_text.count("```") % 2 != 0:
                msgs.append({"role": "assistant", "content": text})
                msgs.append({"role": "user", "content": "Your response was cut off. Please continue EXACTLY where you left off. Do NOT start with backticks, just continue the raw code directly."})
                
                # We will fetch the next chunk in the next iteration.
                # But to avoid backtick corruption, if the next chunk starts with ```, we should strip it.
                # We'll do that by tracking if we are in continuation mode.
                continue
            else:
                break
                
        return _clean_ai_output(full_text)


# ─────────────────────────────────────────────
# Auto-select best available provider
# ─────────────────────────────────────────────

async def call_ai(system: str, user: str, max_tokens: int = 12000,
                  provider: str = DEFAULT_PROVIDER) -> str:
    """
    Call the best available AI provider.
    Priority: explicit provider → auto-detect → pollinations fallback.
    """
    order = []

    if provider == "openai":
        order = ["openai", "gemini", "claude", "pollinations"]
    elif provider == "gemini":
        order = ["gemini", "openai", "claude", "pollinations"]
    elif provider == "claude":
        order = ["claude", "openai", "gemini", "pollinations"]
    elif provider == "pollinations":
        order = ["pollinations"]
    else:  # auto
        if OPENAI_API_KEY:    order.append("openai")
        if GEMINI_API_KEY:    order.append("gemini")
        if ANTHROPIC_API_KEY: order.append("claude")
        order.append("pollinations")

    last_err = None
    for p in order:
        try:
            if p == "openai":
                return await _call_openai(system, user, max_tokens)
            elif p == "gemini":
                return await _call_gemini(system, user, max_tokens)
            elif p == "claude":
                return await _call_claude(system, user, max_tokens)
            elif p == "pollinations":
                return await _call_pollinations(system, user, max_tokens)
        except Exception as e:
            last_err = e
            print(f"[AI Brain] {p} failed: {e}")
            continue

    raise RuntimeError(f"All AI providers failed. Last error: {last_err}")


async def stream_ai(system: str, user: str, max_tokens: int = 4000):
    """
    Async generator yielding text chunks as they arrive from the active LLM.
    Supports Anthropic, Gemini, OpenAI, and Pollinations streaming.
    """
    if ANTHROPIC_API_KEY:
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": ANTHROPIC_API_KEY,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": CLAUDE_MODEL,
                        "max_tokens": max_tokens,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                        "stream": True
                    }
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:].strip()
                            if data_str == "[DONE]":
                                break
                            try:
                                payload = json.loads(data_str)
                                if payload.get("type") == "content_block_delta":
                                    text_chunk = payload.get("delta", {}).get("text", "")
                                    if text_chunk:
                                        yield text_chunk
                            except Exception:
                                pass
            return
        except Exception as err:
            print(f"[AI Brain Stream] Claude stream failed: {err}, falling back to call_ai")

    # Fallback to standard response with chunked yield
    full_text = await call_ai(system, user, max_tokens)
    words = full_text.split(" ")
    for i in range(0, len(words), 3):
        chunk = " ".join(words[i:i+3]) + (" " if i+3 < len(words) else "")
        yield chunk
        await asyncio.sleep(0.01)


async def call_ai_json(system: str, user: str) -> dict:
    """Call AI and parse JSON response, with retry."""
    for attempt in range(3):
        try:
            raw = await call_ai(system, user, max_tokens=4000)
            raw = re.sub(r"```(?:json)?|```", "", raw).strip()
            # Extract first {...} block
            m = re.search(r"\{[\s\S]*\}", raw)
            if m:
                return json.loads(m.group())
            return json.loads(raw)
        except Exception as e:
            if attempt == 2:
                raise
            await asyncio.sleep(1)
    return {}


def get_active_provider() -> str:
    """Return a human-readable name of the active AI provider."""
    if OPENAI_API_KEY:    return f"OpenAI ({OPENAI_MODEL})"
    if GEMINI_API_KEY:    return f"Gemini ({GEMINI_MODEL})"
    if ANTHROPIC_API_KEY: return f"Claude ({CLAUDE_MODEL})"
    return "Pollinations (free)"

