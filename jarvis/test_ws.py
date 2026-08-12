import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8340/ws/voice") as ws:
        msg = {
            "type": "transcript",
            "text": "Create a complete full-stack gym website with modern UI and scalable backend. Tech stack: Frontend: React (with Tailwind CSS for styling), Backend: Node.js with Express, Database: MongoDB, Authentication: JWT-based login/signup system.",
            "isFinal": True
        }
        await ws.send(json.dumps(msg))
        for _ in range(5):
            resp = await ws.recv()
            print("Received:", resp)

asyncio.run(test())
