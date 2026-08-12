import asyncio, httpx

async def test():
    msgs = [{"role": "system", "content": "Return ONLY a JSON map like {'a': 1}"}, {"role": "user", "content": "Go!"}]
    async with httpx.AsyncClient(timeout=180.0) as client:
        res = await client.post('https://text.pollinations.ai/', json={"messages": msgs, "model": "openai", "jsonMode": True})
        print(res.text)

if __name__ == "__main__":
    asyncio.run(test())
