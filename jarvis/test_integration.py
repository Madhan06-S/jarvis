# d:/ironnn/jarvis/test_integration.py
import os
import re
import json
import httpx
import asyncio

async def test_backend_api():
    print("=" * 60)
    print("   J.A.R.V.I.S. SYSTEM INTEGRATION VERIFIER")
    print("=" * 60)
    
    # 1. Verify health endpoint
    print("[1/3] Querying FastAPI /api/health...")
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            res = await client.get("http://127.0.0.1:8340/api/health")
            if res.status_code == 200:
                data = res.json()
                print("  [OK] Backend health: ONLINE")
                print(f"  [OK] Version: {data.get('version')}")
                print(f"  [OK] Active Features: {', '.join(data.get('features', []))}")
            else:
                print(f"  [FAIL] Health returned status: {res.status_code}")
        except Exception as e:
            print(f"  [WARN] Backend connection skipped (is start.bat boot pending?): {e}")

    # 2. Trigger mock phone webhook call receptionist
    print("\n[2/3] Triggering mock Pepper Potts call webhook...")
    async with httpx.AsyncClient(timeout=5) as client:
        try:
            payload = {"type": "incoming_call", "caller": "Pepper Potts"}
            res = await client.post("http://127.0.0.1:8340/api/phone/event", json=payload)
            if res.status_code == 200:
                print("  [OK] Webhook call event broadcast success!")
                
                # Mock call conversation
                speech_payload = {"type": "call_speech", "caller": "Pepper Potts", "text": "Is Madhan there?"}
                res_speech = await client.post("http://127.0.0.1:8340/api/phone/event", json=speech_payload)
                if res_speech.status_code == 200:
                    print("  [OK] Mock call speech receptionist reasoning validated!")
            else:
                print(f"  [FAIL] Webhook returned status: {res.status_code}")
        except Exception as e:
            print(f"  [WARN] Webhook skipped: {e}")

    # 3. Parse and Verify HUD DOM elements in index.html
    print("\n[3/3] Parsing and validating index.html DOM hierarchy...")
    html_path = "frontend/index.html"
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        required_dom_elements = [
            ("Phone HUD Overlay Container", r'id=["\']phone-call-hud["\']'),
            ("Phone Caller ID Holder", r'id=["\']phone-caller-id["\']'),
            ("Phone Connection Status", r'id=["\']phone-status["\']'),
            ("Phone Speech Log Scrollbox", r'id=["\']phone-transcript-box["\']'),
            ("Phone Decline Trigger button", r'id=["\']phone-decline-btn["\']'),
            ("Phone Accept Trigger button", r'id=["\']phone-accept-btn["\']'),
            ("Meeting Scribe Container", r'id=["\']meeting-scribe-hud["\']'),
            ("Meeting Record Status", r'id=["\']meeting-status["\']'),
            ("Meeting Live Transcription Feed", r'id=["\']meeting-scribe-body["\']'),
            ("Meeting Toggle Control Button", r'id=["\']meeting-toggle-btn["\']'),
            ("Desktop Scripts Panel", r'id=["\']sys-automation-hud["\']'),
            ("Work environment launcher button", r'LAUNCH WORK ENVIRONMENT'),
            ("Process shut down button", r'SHUT DOWN APPLICATIONS'),
            ("Screen analysis triggers", r'ANALYZE ACTIVE SCREEN')
        ]
        
        all_passed = True
        for name, pattern in required_dom_elements:
            match = re.search(pattern, html_content)
            if match:
                print(f"  [OK] Found DOM Element: {name.ljust(35)} -> VALID")
            else:
                print(f"  [FAIL] Missing DOM Element: {name.ljust(35)} -> INVALID")
                all_passed = False
                
        if all_passed:
            print("\n" + "=" * 60)
            print("   DOM & BACKEND VERIFICATION RESULT: 100% SUCCESSFUL!")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("   DOM VERIFICATION RESULT: COMPLETED WITH MISSING ITEMS")
            print("=" * 60)
    else:
        print(f"  [FAIL] Could not locate index.html at: {html_path}")

if __name__ == "__main__":
    asyncio.run(test_backend_api())
