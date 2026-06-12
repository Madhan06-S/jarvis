import asyncio
import httpx

async def test():
    msgs = [{"role": "user", "content": "Output a JSON object with key 'test' and value 'hello'. NO REASONING. ONLY JSON."}]
    async with httpx.AsyncClient(timeout=180.0) as client:
        res = await client.post(
            "https://text.pollinations.ai/",
            json={"messages": msgs, "jsonMode": True, "model": "claude"}
        )
        print("Response:")
        print(res.text)

asyncio.run(test())
