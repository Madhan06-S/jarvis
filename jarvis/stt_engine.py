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

import asyncio
import traceback

def wav_bytes_to_float32(audio_bytes: bytes) -> np.ndarray:
    """Converts 16-bit PCM WAV bytes to float32 numpy array normalized for faster-whisper (16kHz)."""
    try:
        with wave.open(io.BytesIO(audio_bytes), 'rb') as wf:
            nframes = wf.getnframes()
            rate = wf.getframerate()
            channels = wf.getnchannels()
            width = wf.getsampwidth()
            frames = wf.readframes(nframes)

            print(f"🎙️ [STT Engine WAV Info] Rate: {rate}Hz | Channels: {channels} | SampWidth: {width * 8}-bit | Frames: {nframes}")

            audio_int16 = np.frombuffer(frames, dtype=np.int16)
            float32_audio = audio_int16.astype(np.float32) / 32768.0

            # If multichannel, average to mono
            if channels > 1 and len(float32_audio) > 0:
                float32_audio = float32_audio.reshape(-1, channels).mean(axis=1)

            # If not 16000 Hz, resample to 16000 Hz
            if rate != 16000 and len(float32_audio) > 0:
                target_len = int(len(float32_audio) * 16000 / rate)
                float32_audio = np.interp(
                    np.linspace(0, len(float32_audio), target_len, endpoint=False),
                    np.arange(len(float32_audio)),
                    float32_audio
                ).astype(np.float32)

            return float32_audio
    except Exception as e:
        print(f"⚠️ [STT Engine] WAV parse warning: {e}. Falling back to raw int16 conversion.")
        try:
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            return audio_int16.astype(np.float32) / 32768.0
        except Exception:
            return np.zeros(0, dtype=np.float32)

def _sync_whisper_transcribe(audio_arr: np.ndarray) -> Dict[str, Any]:
    """Synchronous worker running faster-whisper inference off the asyncio event loop."""
    if WHISPER_MODEL is None or len(audio_arr) == 0:
        return {"text": "", "vad_removed_all": False}

    # 1. First attempt with moderate VAD threshold
    segments, info = WHISPER_MODEL.transcribe(
        audio_arr,
        beam_size=1,
        language="en",
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters=dict(min_silence_duration_ms=400, threshold=0.3)
    )
    seg_list = list(segments)
    text = " ".join([segment.text.strip() for segment in seg_list]).strip()
    vad_removed_all = False

    # 2. If VAD filter stripped everything or returned empty, retry immediately without VAD filter
    if not text:
        vad_removed_all = True
        segments_raw, _ = WHISPER_MODEL.transcribe(
            audio_arr,
            beam_size=1,
            language="en",
            condition_on_previous_text=False,
            vad_filter=False
        )
        raw_list = list(segments_raw)
        text = " ".join([segment.text.strip() for segment in raw_list]).strip()

    return {"text": text, "vad_removed_all": vad_removed_all}

async def transcribe_audio_bytes(audio_bytes: bytes) -> Dict[str, Any]:
    """
    Transcribes raw audio bytes off the event loop using faster-whisper.
    Saves last voice audio to /tmp/last_voice.wav for inspection.
    """
    t_start = time.time()
    text = ""
    engine_used = "none"
    error_msg = None
    duration_sec = 0.0
    vad_removed_all = False

    if not audio_bytes or len(audio_bytes) < 400:
        return {
            "text": "",
            "latency_ms": 0.0,
            "engine": "empty",
            "bytes_received": len(audio_bytes) if audio_bytes else 0,
            "duration_sec": 0.0,
            "vad_removed_all": False,
            "error": "Audio payload too short"
        }

    # Save to /tmp/last_voice.wav for user playback verification
    try:
        with open("/tmp/last_voice.wav", "wb") as f:
            f.write(audio_bytes)
        print(f"💾 [STT Engine] Successfully saved {len(audio_bytes)} bytes to /tmp/last_voice.wav")
    except Exception as save_err:
        print(f"⚠️ [STT Engine] Could not write /tmp/last_voice.wav: {save_err}")

    # 1. FASTER-WHISPER LOCAL TRANSCRIBER (Off-thread execution)
    if WHISPER_AVAILABLE and WHISPER_MODEL:
        try:
            audio_arr = wav_bytes_to_float32(audio_bytes)
            if len(audio_arr) > 0:
                duration_sec = len(audio_arr) / 16000.0
                res = await asyncio.to_thread(_sync_whisper_transcribe, audio_arr)
                text = res.get("text", "")
                vad_removed_all = res.get("vad_removed_all", False)
                engine_used = "faster-whisper (base.en)"
        except Exception as err:
            error_msg = str(err)
            print(f"❌ [STT Engine] faster-whisper inference error: {err}")
            traceback.print_exc()

    # 2. FALLBACK TO SPEECH_RECOGNITION / GOOGLE STT IF WHISPER PRODUCED EMPTY TEXT
    if not text and engine_used == "none":
        try:
            import speech_recognition as sr
            def _sync_google():
                r = sr.Recognizer()
                with sr.AudioFile(io.BytesIO(audio_bytes)) as source:
                    audio = r.record(source)
                return r.recognize_google(audio)
            text = await asyncio.to_thread(_sync_google)
            engine_used = "speech_recognition (google)"
        except Exception as e:
            error_msg = str(e)
            text = ""
            engine_used = "fallback-failed"

    t_end = time.time()
    latency_ms = (t_end - t_start) * 1000.0

    print(f"""
⏱️  [STT BACKEND LOG]
    ├── Bytes Received:   {len(audio_bytes)} bytes
    ├── Audio Duration:   {duration_sec:.2f} s
    ├── Whisper Engine:   {engine_used}
    ├── VAD Removed All:  {vad_removed_all}
    ├── Transcript:       "{text}"
    └── Latency:          {latency_ms:.1f} ms
""")

    return {
        "text": text.strip(),
        "latency_ms": latency_ms,
        "engine": engine_used,
        "bytes_received": len(audio_bytes),
        "duration_sec": duration_sec,
        "vad_removed_all": vad_removed_all,
        "error": error_msg
    }
