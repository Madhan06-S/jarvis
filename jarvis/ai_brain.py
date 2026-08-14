"""
ANTIGRAVITY JARVIS — Multi-AI Brain
Supports: OpenAI GPT-4o, Google Gemini, Anthropic Claude, Pollinations, and Keyless Smart Engine
"""
import os
import re
import json
import asyncio
import httpx
from datetime import datetime
from typing import Optional

def get_openai_key() -> str:
    k = os.getenv("OPENAI_API_KEY", "")
    return k if k and not k.startswith("your-") else ""

def get_gemini_key() -> str:
    k = os.getenv("GEMINI_API_KEY", "")
    return k if k and not k.startswith("your-") else ""

def get_anthropic_key() -> str:
    k = os.getenv("ANTHROPIC_API_KEY", "")
    return k if k and not k.startswith("your-") else ""

OPENAI_MODEL  = os.getenv("OPENAI_MODEL",  "gpt-4o")
GEMINI_MODEL  = os.getenv("GEMINI_MODEL",  "gemini-2.0-flash")
CLAUDE_MODEL  = os.getenv("CLAUDE_MODEL",  "claude-sonnet-4-20250514")

DEFAULT_PROVIDER = os.getenv("AI_PROVIDER", "auto")

# ─────────────────────────────────────────────
# Keyless Local Smart Engine
# ─────────────────────────────────────────────

def generate_keyless_response(prompt: str) -> str:
    p_lower = prompt.lower().strip()
    
    if "hello" in p_lower or "hi" in p_lower or "hey" in p_lower:
        return "Hello sir. J.A.R.V.I.S. is online and ready to assist."
    if "status" in p_lower or "system" in p_lower:
        return "All systems operational, sir. Core reactor at optimal capacity."
    if "who are you" in p_lower or "what is your name" in p_lower:
        return "I am J.A.R.V.I.S., Just A Rather Very Intelligent System."
    if "time" in p_lower:
        return f"The current time is {datetime.now().strftime('%H:%M:%S')}."
    if "date" in p_lower:
        return f"Today is {datetime.now().strftime('%A, %B %d, %Y')}."
    
    return f"Understood, sir. Processing command: '{prompt}'."

# ─────────────────────────────────────────────
# Individual cloud providers
# ─────────────────────────────────────────────

async def _call_openai(system: str, user: str, max_tokens: int = 8000) -> str:
    key = get_openai_key()
    if not key:
        raise ValueError("No valid OpenAI API key")
    async with httpx.AsyncClient(timeout=120.0) as client:
        res = await client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {key}",
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
    key = get_gemini_key()
    if not key:
        raise ValueError("No valid Gemini API key")
    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{GEMINI_MODEL}:generateContent?key={key}"
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
    key = get_anthropic_key()
    if not key:
        raise ValueError("No valid Anthropic API key")
    async with httpx.AsyncClient(timeout=180.0) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
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


# ─────────────────────────────────────────────
# Auto-select best available provider
# ─────────────────────────────────────────────

async def call_ai(system: str, user: str, max_tokens: int = 12000,
                  provider: str = DEFAULT_PROVIDER) -> str:
    order = []

    if provider == "openai":
        order = ["openai", "gemini", "claude"]
    elif provider == "gemini":
        order = ["gemini", "openai", "claude"]
    elif provider == "claude":
        order = ["claude", "openai", "gemini"]
    else:  # auto
        if get_openai_key():    order.append("openai")
        if get_gemini_key():    order.append("gemini")
        if get_anthropic_key(): order.append("claude")

    for p in order:
        try:
            if p == "openai":
                return await _call_openai(system, user, max_tokens)
            elif p == "gemini":
                return await _call_gemini(system, user, max_tokens)
            elif p == "claude":
                return await _call_claude(system, user, max_tokens)
        except Exception as e:
            print(f"[AI Brain] {p} failed: {e}")
            continue

    # Fallback to keyless smart engine
    return generate_keyless_response(user)


async def call_ai_json(system: str, user: str) -> dict:
    """Call AI and parse JSON response, with retry."""
    for attempt in range(3):
        try:
            raw = await call_ai(system, user, max_tokens=4000)
            raw = re.sub(r"```(?:json)?|```", "", raw).strip()
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
    if get_openai_key():    return f"OpenAI ({OPENAI_MODEL})"
    if get_gemini_key():    return f"Gemini ({GEMINI_MODEL})"
    if get_anthropic_key(): return f"Claude ({CLAUDE_MODEL})"
    return "JARVIS Smart Engine (Local)"
