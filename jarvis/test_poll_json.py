import asyncio
import httpx
import json

async def test_poll():
    url = "https://text.pollinations.ai/"
    data = {
        "messages": [{"role": "system", "content": "Return ONLY JSON array of items."}, {"role": "user", "content": "Hello"}],
        "jsonMode": True
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(url, json=data)
        print("Raw:", res.text.encode('utf-8'))

if __name__ == "__main__":
    asyncio.run(test_poll())
