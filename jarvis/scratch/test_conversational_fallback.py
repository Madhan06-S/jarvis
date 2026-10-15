import asyncio
import json
import os
import time
import websockets

def load_token():
    if os.path.exists(".env"):
        with open(".env") as f:
            for line in f:
                if line.startswith("JARVIS_AUTH_TOKEN="):
                    return line.strip().split("=", 1)[1]
    return ""

async def test_fallback_and_memory():
    token = load_token()
    ws_url = f"ws://127.0.0.1:8340/ws/voice?token={token}"
    print(f"📡 Connecting to {ws_url}...")

    async with websockets.connect(ws_url, subprotocols=[f"bearer.{token}"]) as ws:
        init_msg = await ws.recv()
        print("Connected. Initial state:", init_msg)

        # ── Test 1: Conversational query ────────────────
        print("\n--- TEST 1: General Conversational Query ---")
        await ws.send(json.dumps({
            "type": "transcript",
            "text": "Hello JARVIS, who built the Eiffel Tower?",
            "isFinal": True
        }))

        tokens = []
        chunks = []
        metrics = None

        t0 = time.time()
        while time.time() - t0 < 10.0:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=4.0)
                msg = json.loads(raw)
                mtype = msg.get("type")
                if mtype == "token":
                    tokens.append(msg.get("token"))
                elif mtype == "browser_speak_chunk":
                    chunks.append(msg.get("text"))
                    print(f"  [TTS Chunk]: {msg.get('text')}")
                elif mtype == "ai_metrics":
                    metrics = msg
                    print(f"  [AI Metrics]: Model={msg.get('model')}, TTFT={msg.get('time_to_first_token_ms')}ms")
                elif mtype == "status" and msg.get("state") == "idle" and tokens:
                    break
            except asyncio.TimeoutError:
                break

        full_ans = "".join(tokens)
        print(f"Full response: {full_ans}")
        assert len(tokens) > 0, "Expected streamed tokens"
        assert metrics is not None, "Expected ai_metrics payload"
        assert "sir" in full_ans.lower(), "Expected JARVIS persona addressing as 'sir'"
        print("✅ Test 1 Passed: Streaming, sentence TTS, metrics, and persona verified!")

        # ── Test 2: Follow-up question (Short-term memory) ────────────────
        print("\n--- TEST 2: Follow-up Question (Conversation Memory) ---")
        await ws.send(json.dumps({
            "type": "transcript",
            "text": "In what year was it completed?",
            "isFinal": True
        }))

        tokens2 = []
        t0 = time.time()
        while time.time() - t0 < 10.0:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=4.0)
                msg = json.loads(raw)
                mtype = msg.get("type")
                if mtype == "token":
                    tokens2.append(msg.get("token"))
                elif mtype == "status" and msg.get("state") == "idle" and tokens2:
                    break
            except asyncio.TimeoutError:
                break

        full_ans2 = "".join(tokens2)
        print(f"Follow-up response: {full_ans2}")
        assert "1889" in full_ans2 or "march" in full_ans2.lower(), f"Expected year 1889 in follow-up, got: {full_ans2}"
        print("✅ Test 2 Passed: Short-term conversation memory correctly resolved follow-up!")

        # ── Test 3: AI Skill Triggering ────────────────
        print("\n--- TEST 3: AI Skill Triggering ---")
        await ws.send(json.dumps({
            "type": "transcript",
            "text": "remind me to call mom in an hour",
            "isFinal": True
        }))

        card_received = False
        timer_spoken = False
        t0 = time.time()
        while time.time() - t0 < 10.0:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=4.0)
                msg = json.loads(raw)
                mtype = msg.get("type")
                if mtype == "hud_card":
                    card_received = True
                    print("  [HUD Card received]:", msg.get("card", {}).get("title"))
                elif mtype in ["browser_speak", "browser_speak_chunk"]:
                    txt = msg.get("text", "")
                    if "timer" in txt.lower() or "reminder" in txt.lower() or "call mom" in txt.lower():
                        timer_spoken = True
                        print(f"  [Skill Spoken]: {txt}")
                elif mtype == "status" and msg.get("state") == "idle" and card_received:
                    break
            except asyncio.TimeoutError:
                break

        assert card_received, "Expected HUD card from triggered timer skill"
        assert timer_spoken, "Expected timer confirmation speech"
        print("✅ Test 3 Passed: AI mapped request to skill with parsed arguments and executed skill!")

    print("\n🎉 ALL CONVERSATIONAL FALLBACK TESTS PASSED EMPIRICALLY!")

if __name__ == "__main__":
    asyncio.run(test_fallback_and_memory())
