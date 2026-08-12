import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8340/ws/voice") as ws:
        msg = {
            "type": "transcript",
            "text": "Create a complete full-stack gym website with React and Nodejs",
            "isFinal": True
        }
        await ws.send(json.dumps(msg))
        while True:
            try:
                resp = await asyncio.wait_for(ws.recv(), timeout=120)
                print("Received:", resp)
                data = json.loads(resp)
                if data.get("type") == "build_complete" or data.get("type") == "process_complete" or data.get("status") == "error":
                    print("Finished.")
                    break
            except Exception as e:
                print("Error or disconnected:", e)
                break

asyncio.run(test())
