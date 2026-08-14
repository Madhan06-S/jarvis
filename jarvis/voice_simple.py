"""
J.A.R.V.I.S. Voice v2.2 - Simplified Guaranteed Working Version
Strips ALL complexity. Just echoes back to prove the pipe works.
Add API keys LATER once the basic pipe is confirmed working.
"""
import asyncio
import json
import base64
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from datetime import datetime
from pydantic import BaseModel

router = APIRouter()

@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):
    """
    ULTRA-SIMPLE voice endpoint.
    Step 1: Prove WebSocket works (echo mode)
    Step 2: Add features once echo works
    """
    await websocket.accept()
    print(f"[VOICE] Client connected at {datetime.now()}")
    
    # Send immediate confirmation
    await websocket.send_json({
        "type": "connected",
        "message": "J.A.R.V.I.S. Voice online. Say something or type a command.",
        "mode": "echo_test",  # Change to 'full' once confirmed working
        "timestamp": datetime.now().isoformat()
    })
    
    try:
        while True:
            # Receive message (FastAPI WebSocket receive can return dict with text or bytes)
            message = await websocket.receive()
            
            if "text" in message and message["text"]:
                data = json.loads(message["text"])
                msg_type = data.get("type", "unknown")
                
                print(f"[VOICE] Received text: {msg_type}")
                
                if msg_type == "text_command" or msg_type == "browser_stt_result":
                    # User typed a command or sent browser STT
                    text = data.get("text", "")
                    print(f"[VOICE] Text command: {text}")
                    
                    # Echo back with processing simulation
                    await websocket.send_json({
                        "type": "status",
                        "message": f"Received: {text}",
                        "state": "processing"
                    })
                    
                    await asyncio.sleep(0.5)  # Simulate thinking
                    
                    # Simple response (no API keys needed)
                    response = f"I heard you say: '{text}'. Voice pipeline is connected."
                    
                    await websocket.send_json({
                        "type": "response",
                        "text": response,
                        "state": "speaking"
                    })
                    
                    # Send TTS fallback (browser will speak this)
                    await websocket.send_json({
                        "type": "tts_fallback",
                        "text": response
                    })
                    
                    await websocket.send_json({
                        "type": "status",
                        "message": "Ready",
                        "state": "idle"
                    })
                
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                
                elif msg_type == "audio_chunk":
                    # Received base64 audio - just acknowledge
                    await websocket.send_json({
                        "type": "status",
                        "message": "Audio received (STT needs API key)",
                        "state": "processing"
                    })
                    
                    await asyncio.sleep(0.3)
                    
                    await websocket.send_json({
                        "type": "response",
                        "text": "I received your voice audio, but I need a Groq or OpenAI API key to transcribe it. Add GROQ_API_KEY to your .env file.",
                        "state": "speaking"
                    })
                    
                    await websocket.send_json({
                        "type": "tts_fallback",
                        "text": "I received your voice audio, but I need an API key to transcribe it."
                    })
                    
                    await websocket.send_json({
                        "type": "status",
                        "message": "Ready",
                        "state": "idle"
                    })
                
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown message type: {msg_type}"
                    })
            
            elif "bytes" in message and message["bytes"]:
                # Received binary audio
                audio_bytes = message["bytes"]
                print(f"[VOICE] Received binary audio: {len(audio_bytes)} bytes")
                
                await websocket.send_json({
                    "type": "status",
                    "message": f"Received {len(audio_bytes)} bytes of audio",
                    "state": "processing"
                })
                
                await asyncio.sleep(0.3)
                
                await websocket.send_json({
                    "type": "response",
                    "text": "Voice audio received. I need an API key to transcribe speech. Try typing your command instead, or add GROQ_API_KEY to your .env.",
                    "state": "speaking"
                })
                
                await websocket.send_json({
                    "type": "tts_fallback",
                    "text": "Voice audio received. I need an API key to transcribe speech. Try typing your command instead."
                })
                
                await websocket.send_json({
                    "type": "status",
                    "message": "Ready",
                    "state": "idle"
                })
    
    except WebSocketDisconnect:
        print("[VOICE] Client disconnected")
    except Exception as e:
        print(f"[VOICE] Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass


class TextCommand(BaseModel):
    text: str

@router.post("/voice/text-command")
async def text_command(cmd: TextCommand):
    """
    REST endpoint for text commands.
    Use this if WebSocket is broken.
    """
    print(f"[VOICE] REST text command: {cmd.text}")
    
    return {
        "success": True,
        "command": cmd.text,
        "response": f"I received your command: '{cmd.text}'. The voice pipeline is connected.",
        "timestamp": datetime.now().isoformat()
    }
