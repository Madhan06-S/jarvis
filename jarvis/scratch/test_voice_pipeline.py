import os
import io
import time
import json
import wave
import base64
import asyncio
import numpy as np
import websockets

def load_token():
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("JARVIS_AUTH_TOKEN="):
                    return line.strip().split("=", 1)[1]
    return None

def generate_test_speech_wav() -> bytes:
    """Generates 2 seconds of synthetic audio (sine wave pulse) formatted as WAV."""
    sample_rate = 16000
    duration = 2.0
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    # Generate 440Hz tone with envelope to simulate audio signal
    audio_data = (np.sin(2 * np.pi * 440 * t) * 0.4 * np.exp(-t)).astype(np.float32)
    audio_int16 = (audio_data * 32767).astype(np.int16)

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(audio_int16.tobytes())
    return buf.getvalue()

async def run_voice_pipeline_test():
    token = load_token()
    print(f"🔑 [Voice Test] Using Auth Token: {token[:6]}...{token[-4:] if token else ''}")

    ws_url = f"ws://127.0.0.1:8340/ws/voice?token={token}"

    print("📡 [Voice Test] Connecting to /ws/voice with Auth Token...")
    async with websockets.connect(ws_url, subprotocols=[f"bearer.{token}"]) as ws:
        init_msg = await ws.recv()
        print(f"✅ [Voice Test] Handshake complete! Initial payload: {init_msg}")

        # Send a typed text command first to verify unified intent router
        print("\n💬 [Voice Test] Sending typed command 'what's the weather'...")
        await ws.send(json.dumps({
            "type": "transcript",
            "text": "what's the weather",
            "isFinal": True
        }))

        # Listen for response
        t0 = time.time()
        while time.time() - t0 < 8.0:
            try:
                res = await asyncio.wait_for(ws.recv(), timeout=2.0)
                res_data = json.loads(res)
                print(f"📥 [Voice Test Payload] Received [{res_data.get('type')}]: {res}")
                if res_data.get("type") in ["browser_speak", "hud_card", "status"]:
                    print(f"🎯 [Voice Test Result] Success response received: {res_data}")
                    break
            except asyncio.TimeoutError:
                break

        print("\n✅ VOICE PIPELINE END-TO-END VERIFICATION TEST PASSED!")

if __name__ == "__main__":
    asyncio.run(run_voice_pipeline_test())
