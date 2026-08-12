import asyncio
import json
import logging
import speech_recognition as sr
import urllib.request
import os
import tempfile
import time

logging.basicConfig(level=logging.INFO)

def global_listener():
    print("=" * 60)
    print(" GLOBAL JARVIS AWARENESS ONLINE ")
    print(" Listening universally from your laptop background... ")
    print("=" * 60)
    
    r = sr.Recognizer()
    r.dynamic_energy_threshold = True

    while True:
        try:
            with sr.Microphone() as source:
                audio = r.listen(source, phrase_time_limit=10)
            try:
                text = r.recognize_google(audio).lower()
                print(f"[Heard] -> {text}")
                if "jarvis" in text or "travis" in text or "pause" in text or "stop" in text:
                    clean = text.replace("hey jarvis", "").replace("jarvis", "").strip()
                    if not clean and "pause" in text:
                        clean = "pause"
                    if clean:
                        print(f"[Executing] -> {clean}")
                        async def send_cmd():
                            import websockets, json, os, tempfile
                            uri = "ws://127.0.0.1:8340/ws/voice"
                            async with websockets.connect(uri) as ws:
                                await ws.send(json.dumps({"type": "transcript", "text": clean, "isFinal": True}))
                                while True:
                                    try:
                                        data = await asyncio.wait_for(ws.recv(), timeout=15.0)
                                        msg = json.loads(data)
                                        if msg.get("type") == "browser_speak":
                                            reply_str = msg.get("text", "")
                                            print(f"[JARVIS] -> {reply_str}")
                                            text_esc = reply_str.replace('"', '""').replace("\n", " ").replace("\r", "")
                                            script = f'CreateObject("SAPI.SpVoice").Speak("{text_esc}")'
                                            p = os.path.join(tempfile.gettempdir(), "speak_global.vbs")
                                            with open(p, "w", encoding="utf-8") as f: f.write(script)
                                            os.system(f'cscript //nologo "{p}"')
                                        elif msg.get("type") == "status" and msg.get("state") == "idle":
                                            break
                                    except asyncio.TimeoutError:
                                        break
                        asyncio.run(send_cmd())
            except sr.UnknownValueError:
                pass
        except Exception as e:
            print("Microphone error, retrying...", repr(e))
            time.sleep(3)

if __name__ == "__main__":
    global_listener()
