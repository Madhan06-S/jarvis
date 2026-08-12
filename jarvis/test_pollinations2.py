import asyncio
import httpx

async def test_pollinations():
    print("Testing pollinations direct...")
    url = "https://text.pollinations.ai/"
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json={"messages": [{"role": "user", "content": "Hello"}], "model": "gemini"}, headers={"Content-Type": "application/json"})
            print("Status Code:", res.status_code)
            print("Response:", res.text)
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_pollinations())
