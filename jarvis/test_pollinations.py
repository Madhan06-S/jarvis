import asyncio
import httpx

async def test_pollinations():
    print("Testing pollinations...")
    url = "https://text.pollinations.ai/openai/chat/completions"
    headers = {"Content-Type": "application/json"}
    data = {
        "model": "gpt-4o",
        "messages": [{"role": "user", "content": "Hello!"}],
        "jsonMode": True
    }
    
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=data, headers=headers)
            print("Status Code:", res.status_code)
            print("Response:", res.json())
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(test_pollinations())
