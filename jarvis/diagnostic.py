"""
J.A.R.V.I.S. Voice & Input Diagnostic System
Add this to your server.py to debug exactly what's broken.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, HTMLResponse
import os
import sys

diagnostic_router = APIRouter(prefix="/debug", tags=["Diagnostics"])

@diagnostic_router.get("/voice-status")
async def voice_status():
    """Check if voice pipeline can actually work."""
    checks = {
        "websocket_endpoint": "/ws/voice is mounted",
        "webrtc_vad": False,
        "porcupine": False,
        "groq_key": bool(os.getenv("GROQ_API_KEY")),
        "openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "elevenlabs_key": bool(os.getenv("ELEVENLABS_API_KEY")),
        "picovoice_key": bool(os.getenv("PICOVOICE_ACCESS_KEY")),
        "python_version": sys.version,
    }
    
    try:
        import webrtcvad
        checks["webrtc_vad"] = True
    except ImportError:
        checks["webrtc_vad_error"] = "pip install webrtcvad-wheels"
    
    try:
        import pvporcupine
        checks["porcupine"] = True
    except ImportError:
        checks["porcupine_error"] = "pip install pvporcupine"
    
    # Determine what will actually work
    can_wake_word = checks["picovoice_key"] or checks["porcupine"]
    can_stt = checks["groq_key"] or checks["openai_key"]
    can_tts = checks["elevenlabs_key"]
    can_llm = checks["openai_key"]
    
    checks["will_work"] = {
        "wake_word_porcupine": can_wake_word,
        "stt_cloud": can_stt,
        "tts_cloud": can_tts,
        "llm_cloud": can_llm,
        "browser_fallback": True,  # Always works
        "overall": "PARTIAL" if (can_stt or can_llm or can_tts) else "BROWSER_ONLY"
    }
    
    return checks


@diagnostic_router.get("/routes")
async def list_routes(request: Request):
    """List all mounted routes to verify voice endpoint exists."""
    routes = []
    for route in request.app.routes:
        routes.append({
            "path": getattr(route, "path", "unknown"),
            "name": getattr(route, "name", "unknown"),
            "methods": list(getattr(route, "methods", []))
        })
    return {"routes": routes, "total": len(routes)}


@diagnostic_router.get("/ws-test")
async def ws_test_page():
    """Returns a simple HTML page to test WebSocket connection."""
    return HTMLResponse("""
    <!DOCTYPE html>
    <html>
    <head><title>JARVIS WS Test</title></head>
    <body style="background:#0f172a;color:#22d3ee;font-family:monospace;padding:20px;">
        <h2>WebSocket Diagnostic</h2>
        <div id="log"></div>
        <script>
            const log = (msg) => document.getElementById('log').innerHTML += `<p>${msg}</p>`;
            const wsUrl = `ws://${window.location.host}/ws/voice`;
            log(`Connecting to: ${wsUrl}`);
            
            const ws = new WebSocket(wsUrl);
            ws.onopen = () => log('✅ WebSocket CONNECTED');
            ws.onmessage = (e) => log(`📨 Received: ${e.data}`);
            ws.onerror = (e) => log('❌ WebSocket ERROR');
            ws.onclose = (e) => log(`🔌 WebSocket CLOSED (code: ${e.code})`);
            
            // Test mic
            navigator.mediaDevices.getUserMedia({audio:true})
                .then(() => log('✅ Microphone ACCESS GRANTED'))
                .catch(e => log(`❌ Microphone: ${e.message}`));
        </script>
    </body>
    </html>
    """)
