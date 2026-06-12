import asyncio
import httpx

async def test():
    msgs = [{"role": "user", "content": "hi"}]
    async with httpx.AsyncClient() as client:
        res = await client.post('https://text.pollinations.ai/', json={"messages": msgs, "model": "openai-large"})
        print("openai-large:", res.status_code)
        
        res = await client.post('https://text.pollinations.ai/', json={"messages": msgs, "model": "openai"})
        print("openai:", res.status_code)

if __name__ == "__main__":
    asyncio.run(test())
