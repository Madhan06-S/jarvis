from fastapi import APIRouter
from pydantic import BaseModel
import os
import base64
import openai
import httpx
from datetime import datetime
import ai_brain

router = APIRouter(prefix="/voice", tags=["Voice"])

class Command(BaseModel):
    text: str

async def ask_llm(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    print(f"[DEBUG ask_llm] OPENAI_API_KEY raw: {repr(api_key)}")
    if api_key and not api_key.startswith("your-") and not api_key.startswith("sk-your"):
        try:
            client = openai.AsyncOpenAI(api_key=api_key)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are J.A.R.V.I.S., Tony Stark's AI assistant. Be concise."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            return resp.choices[0].message.content
        except Exception as e:
            print(f"[OPENAI ERROR] {e}")

    # Fallback to keyless AI Brain
    try:
        return await ai_brain.call_ai(
            "You are J.A.R.V.I.S., Tony Stark's AI assistant. Be concise.",
            prompt,
            max_tokens=200
        )
    except Exception as e:
        print(f"[AI BRAIN ERROR] {e}")
        return ai_brain.generate_keyless_response(prompt)

async def speak_tts(text: str) -> bytes:
    api_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
    if not api_key or api_key.startswith("your-"):
        return b""
    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
        payload = {"text": text, "model_id": "eleven_turbo_v2_5"}
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, headers=headers, timeout=30)
            return resp.content if resp.status_code == 200 else b""
    except Exception as e:
        print(f"[TTS ERROR] {e}")
        return b""

@router.post("/command")
async def voice_command(cmd: Command):
    print(f"[VOICE] >>> '{cmd.text}'")
    response_text = await ask_llm(cmd.text)
    print(f"[VOICE] <<< '{response_text[:80]}...'")
    audio_bytes = await speak_tts(response_text)
    return {
        "success": True,
        "command": cmd.text,
        "response": response_text,
        "has_audio": len(audio_bytes) > 0,
        "audio_b64": base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else "",
        "timestamp": datetime.now().isoformat()
    }

@router.get("/health")
async def voice_health():
    return {
        "status": "ok",
        "openai": bool(os.getenv("OPENAI_API_KEY") and not os.getenv("OPENAI_API_KEY", "").startswith("your-")),
        "elevenlabs": bool(os.getenv("ELEVENLABS_API_KEY") and not os.getenv("ELEVENLABS_API_KEY", "").startswith("your-")),
        "ai_brain": ai_brain.get_active_provider()
    }
