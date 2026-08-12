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

OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
GEMINI_API_KEY    = os.getenv("GEMINI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

OPENAI_MODEL  = os.getenv("OPENAI_MODEL",  "gpt-4o")
GEMINI_MODEL  = os.getenv("GEMINI_MODEL",  "gemini-2.0-flash")
CLAUDE_MODEL  = os.getenv("CLAUDE_MODEL",  "claude-sonnet-4-20250514")

DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "auto")  # auto | openai | gemini | claude | pollinations

# ─────────────────────────────────────────────
# Individual providers
# ─────────────────────────────────────────────

async def _call_openai(system: str, user: str, max_tokens: int = 8000) -> str:
    if not OPENAI_API_KEY:
        raise ValueError("No OpenAI API key")
    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENAI_API_KEY}",
                     "Content-Type": "application/json"},
            json={
                "model": OPENAI_MODEL,
                "max_tokens": max_tokens,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user}
                ]
            }
        )
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]


async def _call_gemini(system: str, user: str, max_tokens: int = 8000) -> str:
    if not GEMINI_API_KEY:
        raise ValueError("No Gemini API key")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.7}
    }
    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(url, json=payload)
        res.raise_for_status()
        data = res.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]


async def _call_claude(system: str, user: str, max_tokens: int = 8000) -> str:
    if not ANTHROPIC_API_KEY:
        raise ValueError("No Anthropic API key")
    async with httpx.AsyncClient(timeout=180.0) as client:
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
                "messages": [{"role": "user", "content": user}]
            }
        )
        res.raise_for_status()
        return res.json()["content"][0]["text"]


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
                
        # Cleanup any accidental double backticks from stitched continuations
        full_text = full_text.replace("```\n```", "")
        return full_text


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
