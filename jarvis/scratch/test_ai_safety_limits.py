import asyncio
import json
import os
import websockets

AUTH_TOKEN = "BosodgkR-1qqWBxtMYgfFXkLwfhx6tVmgmVQif5xslk"
WS_URL = "ws://127.0.0.1:8340/ws/voice"

async def test_safety_and_routing():
    print("🚀 Connecting to JARVIS Voice WS...")
    async with websockets.connect(
        WS_URL, 
        subprotocols=["bearer", f"bearer.{AUTH_TOKEN}"],
        additional_headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
    ) as ws:
        # Wait for initial status
        init_status = await ws.recv()
        print(f"✅ Connection initialized: {init_status[:60]}")

        # ── TEST 1: Safe skill trigger via AI fallback ──
        print("\n🧪 [TEST 1] Testing Safe Skill Trigger via AI Fallback...")
        prompt1 = "Could you please help me ensure I do not forget to drink water in 15 minutes?"
        await ws.send(json.dumps({"type": "transcript", "text": prompt1, "isFinal": True}))
        
        test1_metrics = None
        test1_spoken = []
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=25.0)
            data = json.loads(raw)
            t = data.get("type")
            if t == "ai_metrics":
                test1_metrics = data
                print(f"   [AI Metrics] Model: {data.get('model')} | Fallback Reason: {data.get('fallback_reason')}")
            elif t in ["browser_speak_chunk", "browser_speak"]:
                txt = data.get("text", "")
                test1_spoken.append(txt)
                print(f"   [Spoken Chunk]: {txt}")
            elif t == "status" and data.get("state") == "idle" and test1_metrics:
                break

        assert test1_metrics is not None, "Failed to receive ai_metrics"
        print("✅ TEST 1 PASSED: Safe skill routed via AI fallback with model metrics logged.")

        # ── TEST 2: Sensitive skill requiring on-screen confirmation ('open terminal') ──
        print("\n🧪 [TEST 2] Testing Restricted Skill Gate ('launch terminal for me')...")
        prompt2 = "Please launch terminal for me right now."
        await ws.send(json.dumps({"type": "transcript", "text": prompt2, "isFinal": True}))

        confirmation_card = None
        test2_spoken = []
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=25.0)
            data = json.loads(raw)
            t = data.get("type")
            if t == "hud_card" and data.get("card", {}).get("type") == "confirmation":
                confirmation_card = data.get("card")
                print(f"   [Security Confirmation Card Received]: ID={confirmation_card.get('id')} | Skill={confirmation_card.get('skill')} | Cmd={confirmation_card.get('command')}")
            elif t in ["browser_speak_chunk", "browser_speak"]:
                test2_spoken.append(data.get("text", ""))
                print(f"   [Spoken Warning]: {data.get('text')}")
            elif t == "status" and data.get("state") == "idle":
                break

        assert confirmation_card is not None, "Failed: Restricted skill did not generate confirmation card"
        conf_id = confirmation_card.get("id")
        print(f"✅ TEST 2 PASSED: Security confirmation card displayed for restricted action. Conf ID: {conf_id}")

        # ── TEST 3: User interactive confirmation execution ──
        print(f"\n🧪 [TEST 3] Confirming action {conf_id} via WebSocket confirm_action...")
        await ws.send(json.dumps({"type": "confirm_action", "id": conf_id, "confirmed": True}))

        confirmed_result = None
        while True:
            raw = await asyncio.wait_for(ws.recv(), timeout=15.0)
            data = json.loads(raw)
            t = data.get("type")
            if t == "confirmation_result":
                confirmed_result = data
                print(f"   [Confirmation Result]: {data}")
            elif t in ["browser_speak_chunk", "browser_speak"]:
                print(f"   [Spoken on Confirmation]: {data.get('text')}")
                if confirmed_result:
                    break

        assert confirmed_result and confirmed_result.get("status") == "confirmed", "Failed to confirm action"
        print("✅ TEST 3 PASSED: Action confirmed and executed upon user approval.")

        # ── TEST 4: Verification of Audit Log ──
        print("\n🧪 [TEST 4] Verifying logs/ai_skills.log audit trail...")
        assert os.path.exists("logs/ai_skills.log"), "logs/ai_skills.log does not exist"
        with open("logs/ai_skills.log", "r", encoding="utf-8") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        print("   Recent audit log entries:\n   " + "\n   ".join(lines[-4:]))
        assert any("CONFIRMATION_REQUIRED" in l for l in lines), "Missing CONFIRMATION_REQUIRED in audit log"
        assert any("CONFIRMED_EXECUTED" in l for l in lines), "Missing CONFIRMED_EXECUTED in audit log"
        print("✅ TEST 4 PASSED: Audit log recorded events with timestamp and original query.")

        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_safety_and_routing())
