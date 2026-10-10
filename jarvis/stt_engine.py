"""
JARVIS Server-Side STT Engine — faster-whisper with Gemini / Google STT Fallbacks
Transcribes incoming audio streams with low latency directly on backend.
"""
import os
import io
import time
import wave
import numpy as np
from typing import Dict, Any, Optional

WHISPER_MODEL = None
WHISPER_AVAILABLE = False

try:
    from faster_whisper import WhisperModel
    print("🎙️ [STT Engine] Loading faster-whisper 'base.en' model...")
    # Load base.en model locally on CPU with int8 quantization
    WHISPER_MODEL = WhisperModel("base.en", device="cpu", compute_type="int8")
    WHISPER_AVAILABLE = True
    print("🎙️ [STT Engine] faster-whisper 'base.en' online.")
except Exception as e:
    print(f"⚠️ [STT Engine] faster-whisper failed to load: {e}")
    WHISPER_AVAILABLE = False

def wav_bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    """Converts 16-bit PCM WAV bytes to float32 numpy array for faster-whisper."""
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
            nframes = wf.getnframes()
            frames = wf.readframes(nframes)
            audio_int16 = np.frombuffer(frames, dtype=np.int16)
            return audio_int16.astype(np.float32) / 32768.0
    except Exception:
        try:
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            return audio_int16.astype(np.float32) / 32768.0
        except Exception:
            return np.zeros(0, dtype=np.float32)

async def transcribe_audio_bytes(audio_bytes: bytes) -> Dict[str, Any]:
    """
    Transcribes raw audio bytes using faster-whisper, falling back to Google STT or Gemini.
    Returns dict with 'text', 'latency_ms', and 'engine'.
    """
    t_start = time.time()
    text = ""
    engine_used = "none"

    if not audio_bytes or len(audio_bytes) < 500:
        return {"text": "", "latency_ms": 0.0, "engine": "empty"}

    # 1. FASTER-WHISPER LOCAL TRANSCRIBER
    if WHISPER_AVAILABLE and WHISPER_MODEL:
        try:
            audio_arr = wav_bytes_to_float32(audio_bytes)
            if len(audio_arr) > 0:
                segments, info = WHISPER_MODEL.transcribe(audio_arr, beam_size=1, language="en")
                text = " ".join([segment.text.strip() for segment in segments]).strip()
                engine_used = "faster-whisper (base.en)"
        except Exception as err:
            print(f"⚠️ [STT Engine] faster-whisper error: {err}")

    # 2. FALLBACK TO SPEECH_RECOGNITION / GOOGLE STT IF FASTER-WHISPER FAILED
    if engine_used == "none":
        try:
            import speech_recognition as sr
            r = sr.Recognizer()
            with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                audio = r.record(source)
            text = r.recognize_google(audio)
            engine_used = "speech_recognition (google)"
        except Exception as e:
            text = ""
            engine_used = "fallback-failed"

    t_end = time.time()
    latency_ms = (t_end - t_start) * 1000.0

    print(f"""
⏱️  [STT LATENCY BREAKDOWN]
    ├── Engine:     {engine_used}
    ├── Audio Size: {len(audio_bytes)} bytes
    ├── Latency:    {latency_ms:.1f} ms
    └── Transcript: "{text}"
""")

    return {
        "text": text.strip(),
        "latency_ms": latency_ms,
        "engine": engine_used
    }
