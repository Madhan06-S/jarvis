"""
J.A.R.V.I.S. Voice Pipeline v2.1
Zero-API-Key Mode + Push-to-Talk + Conversation Memory
"""
import asyncio
import json
import base64
import os
import tempfile
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional, List
from datetime import datetime

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
    Try Groq → OpenAI → return empty (frontend will use browser STT).
    """
    groq_key = os.getenv("GROQ_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")
    
    if groq_key:
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
    
    if openai_key:
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
    
    return ""  # Triggers frontend browser STT fallback

# ─── LLM WITH MEMORY ───
async def stream_llm_with_memory(prompt: str, memory: ConversationMemory, websocket: WebSocket):
    """Stream LLM with conversation context."""
    openai_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    
    messages = [
        {"role": "system", "content": "You are J.A.R.V.I.S., Tony Stark's AI assistant. Keep voice responses concise (1-2 sentences). You have memory of the current conversation."}
    ]
    messages.extend(memory.get_context())
    messages.append({"role": "user", "content": prompt})
    
    full_response = []
    sentence_buffer = []
    
    if os.getenv("OPENAI_API_KEY"):
        try:
            import openai
            client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            stream = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages,
                stream=True,
                max_tokens=150
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                full_response.append(delta)
                sentence_buffer.append(delta)
                await websocket.send_json({"type": "llm_token", "text": delta})
                
                if any(p in delta for p in ".!?"):
                    sentence = "".join(sentence_buffer).strip()
                    if sentence:
                        await stream_tts_any(sentence, websocket)
                        sentence_buffer = []
            
            if sentence_buffer:
                remaining = "".join(sentence_buffer).strip()
                if remaining:
                    await stream_tts_any(remaining, websocket)
            
            response_text = "".join(full_response)
            memory.add("user", prompt)
            memory.add("assistant", response_text)
            return response_text
            
        except Exception as e:
            print(f"LLM failed: {e}")
    
    # Fallback: smart static response
    fallback = "I'm operational, sir. All primary sub-systems are online and standing by."
    await websocket.send_json({"type": "llm_token", "text": fallback})
    await stream_tts_any(fallback, websocket)
    memory.add("user", prompt)
    memory.add("assistant", fallback)
    return fallback

# ─── TTS FALLBACK CHAIN ───
async def stream_tts_any(text: str, websocket: WebSocket):
    """Try ElevenLabs → Browser TTS fallback."""
    eleven_key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")
    
    if eleven_key:
        try:
            import httpx
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            headers = {"xi-api-key": eleven_key, "Content-Type": "application/json"}
            payload = {
                "text": text,
                "model_id": "eleven_turbo_v2_5",
                "optimize_streaming_latency": 4,
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
            }
            async with httpx.AsyncClient() as client:
                async with client.stream("POST", url, json=payload, headers=headers, timeout=30) as resp:
                    if resp.status_code == 200:
                        async for chunk in resp.aiter_bytes(chunk_size=8192):
                            if chunk:
                                await websocket.send_json({
                                    "type": "tts_chunk",
                                    "audio": base64.b64encode(chunk).decode("utf-8"),
                                    "done": False
                                })
                        await websocket.send_json({"type": "tts_chunk", "audio": "", "done": True})
                        return
        except Exception as e:
            print(f"ElevenLabs failed: {e}")
    
    # Final fallback: browser TTS (zero API key)
    await websocket.send_json({"type": "tts_fallback", "text": text})

# ─── VOICE SESSION (with Push-to-Talk support) ───
class VoiceSession:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.memory = ConversationMemory(max_turns=5)
        self.state = "idle"  # idle | wake | listening | push_to_talk | processing
        self.audio_buffer = bytearray()
        self.silence_count = 0
        self.speech_count = 0
        self.frame_size = int(16000 * 30 / 1000) * 2  # 30ms @ 16kHz, 16-bit
        self.push_to_talk_active = False
    
    def process_frame(self, frame: bytes) -> Optional[str]:
        is_speech = vad.is_speech(frame, 16000) if vad else True
        
        if self.state in ("listening", "push_to_talk"):
            if is_speech:
                self.silence_count = 0
                self.speech_count += 1
                self.audio_buffer.extend(frame)
            else:
                self.silence_count += 1
                if self.speech_count > 10:
                    self.audio_buffer.extend(frame)
                    if self.silence_count > 25:  # ~750ms silence
                        return "utterance_end"
            
            if self.push_to_talk_active and len(self.audio_buffer) > self.frame_size * 1000:
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
        "message": "Say 'Hey Jarvis' or hold Space",
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
                msg_type = data.get("type")
                
                # ─── PUSH-TO-TALK ───
                if msg_type == "push_to_talk_start":
                    session.state = "push_to_talk"
                    session.push_to_talk_active = True
                    session.audio_buffer.clear()
                    await websocket.send_json({
                        "type": "status",
                        "message": "Recording... (release Space to send)",
                        "state": "listening"
                    })
                
                elif msg_type == "push_to_talk_end":
                    session.push_to_talk_active = False
                    session.state = "processing"
                    audio = session.get_audio()
                    
                    if len(audio) > 0:
                        await websocket.send_json({"type": "status", "message": "Processing...", "state": "processing"})
                        text = await transcribe_any(audio)
                        
                        if not text:
                            await websocket.send_json({"type": "stt_fallback", "reason": "no_api_key"})
                            session.state = "idle"
                            continue
                        
                        await websocket.send_json({"type": "transcript", "text": text})
                        await stream_llm_with_memory(text, session.memory, websocket)
                        
                        session.state = "idle"
                        await websocket.send_json({
                            "type": "status",
                            "message": "Say 'Hey Jarvis' or hold Space",
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
                
                elif msg_type == "utterance_complete":
                    session.state = "processing"
                    audio = session.get_audio()
                    
                    if len(audio) > 0:
                        text = await transcribe_any(audio)
                        
                        if not text:
                            await websocket.send_json({"type": "stt_fallback", "reason": "no_api_key"})
                            session.state = "idle"
                            continue
                        
                        await websocket.send_json({"type": "transcript", "text": text})
                        await stream_llm_with_memory(text, session.memory, websocket)
                    
                    session.state = "idle"
                    await websocket.send_json({
                        "type": "status",
                        "message": "Say 'Hey Jarvis' or hold Space",
                        "state": "idle"
                    })
                
                # ─── BROWSER STT RESULT ───
                elif msg_type == "browser_stt_result":
                    text = data.get("text", "").strip()
                    if text:
                        await websocket.send_json({"type": "transcript", "text": text})
                        await stream_llm_with_memory(text, session.memory, websocket)
                    
                    session.state = "idle"
                    await websocket.send_json({
                        "type": "status",
                        "message": "Say 'Hey Jarvis' or hold Space",
                        "state": "idle"
                    })
                
                # ─── CLEAR MEMORY ───
                elif msg_type == "clear_memory":
                    session.memory.clear()
                    await websocket.send_json({"type": "status", "message": "Conversation memory cleared", "state": "idle"})
            
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
                                else:
                                    await websocket.send_json({"type": "stt_fallback", "reason": "no_api_key"})
                                
                                session.state = "idle"
                                await websocket.send_json({
                                    "type": "status",
                                    "message": "Say 'Hey Jarvis' or hold Space",
                                    "state": "idle"
                                })
    
    except WebSocketDisconnect:
        print("Voice client disconnected")
    except Exception as e:
        print(f"Voice error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
