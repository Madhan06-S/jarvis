"""
J.A.R.V.I.S. Voice Pipeline v2.2
Zero-API-Key Mode + Push-to-Talk + Conversation Memory + Keyless Fallback
"""
import asyncio
import json
import base64
import os
import tempfile
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional, List
from datetime import datetime
import ai_brain

try:
    import webrtcvad
    vad = webrtcvad.Vad(2)
except ImportError:
    vad = None

router = APIRouter()

# ─── CONVERSATION MEMORY ───
class ConversationMemory:
    """Stores last N voice exchanges per session."""
    def __init__(self, max_turns: int = 5):
        self.turns: List[dict] = []
        self.max_turns = max_turns
    
    def add(self, role: str, content: str):
        self.turns.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.turns) > self.max_turns * 2:
            self.turns = self.turns[-self.max_turns * 2:]
    
    def get_context(self) -> List[dict]:
        return [{"role": t["role"], "content": t["content"]} for t in self.turns]
    
    def clear(self):
        self.turns = []

# ─── STT FALLBACK CHAIN ───
async def transcribe_any(audio_bytes: bytes) -> str:
    """
    Try Groq → OpenAI → return empty.
    """
    groq_key = os.getenv("GROQ_API_KEY", "").strip()
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    if groq_key and not groq_key.startswith("your-"):
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes)
                tmp = f.name
            with open(tmp, "rb") as af:
                r = await client.audio.transcriptions.create(model="whisper-large-v3", file=af, response_format="text")
            if os.path.exists(tmp):
                os.unlink(tmp)
            return r.strip()
        except Exception as e:
            print(f"Groq STT failed: {e}")
    
    if openai_key and not openai_key.startswith("your-"):
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=openai_key)
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
                f.write(audio_bytes)
                tmp = f.name
            with open(tmp, "rb") as af:
                r = await client.audio.transcriptions.create(model="whisper-1", file=af, response_format="text")
            if os.path.exists(tmp):
                os.unlink(tmp)
            return r.strip()
        except Exception as e:
            print(f"OpenAI STT failed: {e}")
    
    return ""

async def stream_tts_any(text: str, websocket: WebSocket):
    """
    Try ElevenLabs → return tts_fallback so browser speaks.
    """
    eleven_key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
    
    if eleven_key and not eleven_key.startswith("your-"):
        try:
            import httpx
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            headers = {"xi-api-key": eleven_key, "Content-Type": "application/json"}
            payload = {"text": text, "model_id": "eleven_turbo_v2_5"}
            
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url, json=payload, headers=headers) as resp:
                    if resp.status_code == 200:
                        async for chunk in resp.aiter_bytes():
                            b64 = base64.b64encode(chunk).decode("utf-8")
                            await websocket.send_json({"type": "tts_chunk", "audio": b64})
                        await websocket.send_json({"type": "tts_chunk", "done": True})
                        return
        except Exception as e:
            print(f"ElevenLabs TTS failed: {e}")
    
    # Fallback: browser TTS
    await websocket.send_json({"type": "tts_fallback", "text": text})

# ─── LLM WITH MEMORY ───
async def stream_llm_with_memory(prompt: str, memory: ConversationMemory, websocket: WebSocket):
    """Stream LLM with conversation context and keyless fallback."""
    openai_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    messages = [
        {"role": "system", "content": "You are J.A.R.V.I.S., Tony Stark's AI assistant. Keep responses concise (1-2 sentences)."}
    ]
    messages.extend(memory.get_context())
    messages.append({"role": "user", "content": prompt})
    
    if openai_key and not openai_key.startswith("your-"):
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=openai_key)
            stream = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                max_tokens=150
            )
            full_response = []
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_response.append(delta)
                    await websocket.send_json({"type": "llm_token", "text": delta})
            
            response_text = "".join(full_response).strip()
            if response_text:
                await websocket.send_json({"type": "response", "text": response_text})
                await stream_tts_any(response_text, websocket)
                memory.add("user", prompt)
                memory.add("assistant", response_text)
                return response_text
        except Exception as e:
            print(f"OpenAI LLM failed: {e}")
    
    # Fallback to keyless AI Brain
    try:
        response_text = await ai_brain.call_ai(
            "You are J.A.R.V.I.S., Tony Stark's AI assistant. Keep responses concise (1-2 sentences).",
            prompt,
            max_tokens=150
        )
    except Exception as e:
        print(f"AI Brain fallback failed: {e}")
        response_text = ai_brain.generate_keyless_response(prompt)
    
    await websocket.send_json({"type": "llm_token", "text": response_text})
    await websocket.send_json({"type": "response", "text": response_text})
    await stream_tts_any(response_text, websocket)
    memory.add("user", prompt)
    memory.add("assistant", response_text)
    return response_text

class VoiceSession:
    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.memory = ConversationMemory()
        self.state = "idle"
        self.push_to_talk_active = False
        self.audio_buffer = bytearray()
        self.silence_count = 0
        self.speech_count = 0
        self.frame_size = 640  # 20ms @ 16kHz 16-bit mono

    def process_frame(self, pcm_bytes: bytes) -> Optional[str]:
        if len(pcm_bytes) != self.frame_size:
            return None
        
        self.audio_buffer.extend(pcm_bytes)
        
        if vad:
            is_speech = vad.is_speech(pcm_bytes, 16000)
            if is_speech:
                self.speech_count += 1
                self.silence_count = 0
            else:
                self.silence_count += 1
            
            if self.speech_count > 5:
                if self.silence_count > 25:  # ~750ms silence
                    return "utterance_end"
        
        return None
    
    def get_audio(self) -> bytes:
        audio = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        self.silence_count = 0
        self.speech_count = 0
        return audio

# ─── WEBSOCKET ENDPOINT ───
@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    await websocket.accept()
    session = VoiceSession(websocket)
    
    await websocket.send_json({
        "type": "status",
        "message": "Say 'Hey Jarvis' or type a command",
        "state": "idle",
        "api_keys": {
            "stt": bool(os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")),
            "llm": bool(os.getenv("OPENAI_API_KEY")),
            "tts": bool(os.getenv("ELEVENLABS_API_KEY"))
        }
    })
    
    try:
        while True:
            message = await websocket.receive()
            
            if "text" in message and message["text"]:
                data = json.loads(message["text"])
                msg_type = data.get("type", "")
                
                # ─── TEXT COMMANDS & TRANSCRIPTS ───
                if msg_type in ("transcript", "text_command", "text", "browser_stt_result", "user_message"):
                    text = data.get("text", "").strip()
                    if text:
                        print(f"[VOICE WS] Processing text command: '{text}'")
                        await websocket.send_json({"type": "status", "message": f"Processing: {text}", "state": "processing"})
                        await websocket.send_json({"type": "transcript", "text": text})
                        await stream_llm_with_memory(text, session.memory, websocket)
                    
                    session.state = "idle"
                    await websocket.send_json({
                        "type": "status",
                        "message": "Say 'Hey Jarvis' or type a command",
                        "state": "idle"
                    })
                
                # ─── PUSH-TO-TALK ───
                elif msg_type == "push_to_talk_start":
                    session.state = "push_to_talk"
                    session.push_to_talk_active = True
                    session.audio_buffer.clear()
                    await websocket.send_json({
                        "type": "status",
                        "message": "Recording...",
                        "state": "listening"
                    })
                
                elif msg_type == "push_to_talk_end":
                    session.push_to_talk_active = False
                    session.state = "processing"
                    audio = session.get_audio()
                    
                    if len(audio) > 0:
                        await websocket.send_json({"type": "status", "message": "Processing...", "state": "processing"})
                        text = await transcribe_any(audio)
                        if text:
                            await websocket.send_json({"type": "transcript", "text": text})
                            await stream_llm_with_memory(text, session.memory, websocket)
                        else:
                            await websocket.send_json({"type": "stt_fallback", "reason": "no_api_key"})
                    
                    session.state = "idle"
                    await websocket.send_json({
                        "type": "status",
                        "message": "Say 'Hey Jarvis' or type a command",
                        "state": "idle"
                    })
                
                # ─── WAKE WORD ───
                elif msg_type == "wake_detected":
                    session.state = "listening"
                    session.audio_buffer.clear()
                    await websocket.send_json({
                        "type": "wake_word",
                        "message": "Yes, sir?",
                        "state": "listening"
                    })
                
                elif msg_type == "clear_memory":
                    session.memory.clear()
                    await websocket.send_json({"type": "status", "message": "Memory cleared", "state": "idle"})

            elif "bytes" in message and message["bytes"]:
                message_bytes = message["bytes"]
                if session.state in ("listening", "push_to_talk"):
                    for i in range(0, len(message_bytes), session.frame_size):
                        frame = message_bytes[i:i + session.frame_size]
                        if len(frame) < session.frame_size:
                            break
                        result = session.process_frame(frame)
                        if result == "utterance_end" and not session.push_to_talk_active:
                            audio = session.get_audio()
                            if len(audio) > 0:
                                session.state = "processing"
                                text = await transcribe_any(audio)
                                if text:
                                    await websocket.send_json({"type": "transcript", "text": text})
                                    await stream_llm_with_memory(text, session.memory, websocket)
                            session.state = "idle"

    except WebSocketDisconnect:
        print("[VOICE WS] Client disconnected")
    except Exception as e:
        print(f"[VOICE WS] Error: {e}")
