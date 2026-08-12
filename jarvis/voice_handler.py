"""
J.A.R.V.I.S. Voice Pipeline v2.0
Low-latency streaming voice with "Hey Jarvis" wake word detection.
"""
import asyncio
import json
import base64
import io
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Optional
import wave
import tempfile
import os

try:
    import webrtcvad
    vad = webrtcvad.Vad(2)
except ImportError:
    vad = None

router = APIRouter()

# ─── CONFIG ───
WAKE_WORD = "hey jarvis"
SAMPLE_RATE = 16000
FRAME_DURATION = 30  # ms
SILENCE_FRAMES_THRESHOLD = 25  # ~750ms silence = end of utterance
PRE_BUFFER_FRAMES = 10  # Keep 300ms before speech

# ─── STT: Groq Whisper (fastest) or OpenAI ───
async def stream_stt(audio_bytes: bytes) -> str:
    """Ultra-fast transcription using Groq Whisper or OpenAI."""
    try:
        import openai
        api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            return ""
            
        base_url = "https://api.groq.com/openai/v1" if os.getenv("GROQ_API_KEY") else "https://api.openai.com/v1"
        client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        
        with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name
        
        try:
            with open(tmp_path, "rb") as audio_file:
                model = "whisper-large-v3" if os.getenv("GROQ_API_KEY") else "whisper-1"
                transcript = await client.audio.transcriptions.create(
                    model=model,
                    file=audio_file,
                    response_format="text",
                    language="en"
                )
            return transcript.strip()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    except Exception as e:
        print(f"[STT Error] {e}")
        return ""


# ─── TTS: ElevenLabs Streaming ───
import httpx

ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "pNInz6obpgDQGcFmaJgB")  # Adam voice
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

async def stream_tts(text: str, websocket: WebSocket):
    """Stream ElevenLabs audio chunks as soon as they're ready."""
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        await websocket.send_json({"type": "tts_fallback", "text": text})
        return
    
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVENLABS_VOICE_ID}/stream"
    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_turbo_v2_5",
        "optimize_streaming_latency": 4,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }
    
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream("POST", url, json=payload, headers=headers, timeout=30) as resp:
                if resp.status_code != 200:
                    await websocket.send_json({"type": "tts_fallback", "text": text})
                    return
                
                async for chunk in resp.aiter_bytes(chunk_size=8192):
                    if chunk:
                        await websocket.send_json({
                            "type": "tts_chunk",
                            "audio": base64.b64encode(chunk).decode("utf-8"),
                            "done": False
                        })
                
                await websocket.send_json({"type": "tts_chunk", "audio": "", "done": True})
    except Exception as e:
        print(f"[TTS Error] {e}")
        await websocket.send_json({"type": "tts_fallback", "text": text})


# ─── LLM: Streaming (OpenAI / Claude) ───
async def stream_llm(prompt: str, websocket: WebSocket) -> str:
    """Stream LLM response and accumulate text for sentence-level TTS."""
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        fallback_text = f"I heard you say: {prompt}. All systems operational, sir."
        await websocket.send_json({"type": "llm_token", "text": fallback_text})
        await stream_tts(fallback_text, websocket)
        return fallback_text

    try:
        import openai
        client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", api_key))
        
        full_response = []
        sentence_buffer = []
        
        stream = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are J.A.R.V.I.S., Tony Stark's AI assistant. Keep responses concise (1-2 sentences) for voice."},
                {"role": "user", "content": prompt}
            ],
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
                    await stream_tts(sentence, websocket)
                    sentence_buffer = []
        
        if sentence_buffer:
            remaining = "".join(sentence_buffer).strip()
            if remaining:
                await stream_tts(remaining, websocket)
        
        return "".join(full_response)
    except Exception as e:
        print(f"[LLM Error] {e}")
        err_msg = "Apologies, sir. My cognitive processing experienced a brief interruption."
        await websocket.send_json({"type": "llm_token", "text": err_msg})
        await stream_tts(err_msg, websocket)
        return err_msg


# ─── WAKE WORD DETECTION ───
class WakeWordDetector:
    def __init__(self):
        self.porcupine = None
        self._init_porcupine()
    
    def _init_porcupine(self):
        try:
            import pvporcupine
            access_key = os.getenv("PICOVOICE_ACCESS_KEY")
            if access_key:
                self.porcupine = pvporcupine.create(
                    access_key=access_key,
                    keywords=["jarvis"]
                )
                print("✅ Porcupine wake word loaded")
        except Exception as e:
            print(f"ℹ️ Porcupine optional setup ({e}), STT fallback ready")
    
    def process(self, pcm: bytes) -> bool:
        if self.porcupine:
            pcm_data = np.frombuffer(pcm, dtype=np.int16)
            result = self.porcupine.process(pcm_data)
            return result >= 0
        return False

wake_detector = WakeWordDetector()


# ─── AUDIO FRAME PROCESSING ───
class VoiceSession:
    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.state = "listening_wake"  # listening_wake | listening_command | processing
        self.audio_buffer = bytearray()
        self.pre_buffer = bytearray()
        self.silence_count = 0
        self.speech_count = 0
        self.frame_size = int(SAMPLE_RATE * FRAME_DURATION / 1000) * 2  # 16-bit
    
    def process_frame(self, frame: bytes) -> Optional[str]:
        is_speech = vad.is_speech(frame, SAMPLE_RATE) if vad else True
        
        if self.state == "listening_wake":
            self.pre_buffer.extend(frame)
            if len(self.pre_buffer) > self.frame_size * PRE_BUFFER_FRAMES:
                self.pre_buffer = self.pre_buffer[-self.frame_size * PRE_BUFFER_FRAMES:]
            
            if wake_detector.porcupine:
                if wake_detector.process(frame):
                    return "wake"
            else:
                if is_speech:
                    self.audio_buffer.extend(frame)
                    if len(self.audio_buffer) > self.frame_size * 50:  # ~1.5s
                        return "wake_check"
                else:
                    self.audio_buffer.clear()
        
        elif self.state == "listening_command":
            if is_speech:
                self.silence_count = 0
                self.speech_count += 1
                self.audio_buffer.extend(frame)
            else:
                self.silence_count += 1
                if self.speech_count > 10:
                    self.audio_buffer.extend(frame)
                    if self.silence_count > SILENCE_FRAMES_THRESHOLD:
                        return "utterance_end"
        
        return None
    
    def get_audio(self) -> bytes:
        if self.state == "listening_wake" and not wake_detector.porcupine:
            audio = bytes(self.pre_buffer) + bytes(self.audio_buffer)
        else:
            audio = bytes(self.audio_buffer)
        self.audio_buffer.clear()
        self.pre_buffer.clear()
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
        "message": "Listening for 'Hey Jarvis'...",
        "state": "idle"
    })
    
    try:
        while True:
            message = await websocket.receive()
            
            if "text" in message and message["text"]:
                data = json.loads(message["text"])
                if data.get("type") == "audio_chunk":
                    audio_bytes = base64.b64decode(data["audio"])
                    await _handle_audio_bytes(audio_bytes, session, websocket)
            
            elif "bytes" in message and message["bytes"]:
                audio_bytes = message["bytes"]
                await _handle_audio_bytes(audio_bytes, session, websocket)
    
    except WebSocketDisconnect:
        print("Voice client disconnected")
    except Exception as e:
        print(f"Voice error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass


async def _handle_audio_bytes(audio_bytes: bytes, session: VoiceSession, websocket: WebSocket):
    for i in range(0, len(audio_bytes), session.frame_size):
        frame = audio_bytes[i:i + session.frame_size]
        if len(frame) < session.frame_size:
            break
        
        result = session.process_frame(frame)
        
        if result == "wake":
            session.state = "listening_command"
            await websocket.send_json({
                "type": "wake_word",
                "message": "Yes, sir?",
                "state": "listening"
            })
        
        elif result == "wake_check":
            audio = session.get_audio()
            text = await stream_stt(audio)
            if WAKE_WORD in text.lower():
                session.state = "listening_command"
                await websocket.send_json({
                    "type": "wake_word",
                    "message": "Yes, sir?",
                    "state": "listening"
                })
        
        elif result == "utterance_end":
            audio = session.get_audio()
            if len(audio) > 0:
                await websocket.send_json({
                    "type": "status",
                    "message": "Processing...",
                    "state": "processing"
                })
                
                text = await stream_stt(audio)
                await websocket.send_json({"type": "transcript", "text": text})
                
                if text.strip():
                    await stream_llm(text, websocket)
                
                session.state = "listening_wake"
                await websocket.send_json({
                    "type": "status",
                    "message": "Listening for 'Hey Jarvis'...",
                    "state": "idle"
                })
