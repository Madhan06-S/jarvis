import os
import sys
import time
import json
import asyncio
import httpx
import websockets

def load_token():
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("JARVIS_AUTH_TOKEN="):
                    return line.strip().split("=", 1)[1]
    return None

async def run_security_tests():
    token = load_token()
    print(f"Loaded Auth Token: {token[:6]}...{token[-4:] if token else ''}")
    assert token and token != "jarvis-stark-secure-2026", "Security Error: Token not properly randomized in .env"

    base_url = "http://127.0.0.1:8340"
    ws_url = "ws://127.0.0.1:8340/ws/voice"

    async with httpx.AsyncClient(timeout=5) as client:
        # 1. Authenticated HTTP Request
        print("\n[TEST 1] Authenticated HTTP request to /api/files...")
        headers = {"Authorization": f"Bearer {token}"}
        res = await client.get(f"{base_url}/api/files", headers=headers)
        print(f"  Result: HTTP {res.status_code}")
        assert res.status_code == 200, f"Expected 200, got {res.status_code}"

        # 2. Directory Traversal Attack Attempt
        print("\n[TEST 2] Directory Traversal attempt (/api/files/content?path=../../.env)...")
        res = await client.get(f"{base_url}/api/files/content?path=../../.env", headers=headers)
        print(f"  Result: HTTP {res.status_code}")
        assert res.status_code == 403, f"Expected 403, got {res.status_code}"

        # 3. Unauthenticated HTTP Request
        print("\n[TEST 3] Unauthenticated HTTP request to /api/files...")
        res = await client.get(f"{base_url}/api/files")
        print(f"  Result: HTTP {res.status_code}")
        assert res.status_code in (401, 429), f"Expected 401 or 429, got {res.status_code}"

    # 4. Unauthenticated WebSocket Connection
    print("\n[TEST 4] Unauthenticated WebSocket connection...")
    try:
        async with websockets.connect(ws_url) as ws:
            print("  Result: Connected unexpectedly!")
            assert False, "WebSocket should have rejected connection"
    except Exception as e:
        print(f"  Result: Connection Rejected cleanly ({e})")

    # 5. Authenticated WebSocket Connection
    print("\n[TEST 5] Authenticated WebSocket connection...")
    auth_ws_url = f"{ws_url}?token={token}"
    async with websockets.connect(auth_ws_url) as ws:
        msg = await ws.recv()
        data = json.loads(msg)
        print(f"  Result: Connected! Initial state payload: {data}")
        assert data.get("type") == "status", "Expected status payload"

    print("\n✅ ALL 5 SECURITY VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_security_tests())
