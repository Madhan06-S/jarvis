import asyncio
import builder
import os

async def test():
    plan = {
        'name': 'test-app', 'title': 'Test App', 'stack': 'nextjs', 'db': 'none',
        'features': ['login'], 'theme': 'dark', 'pages': ['/', '/login'], 'api_routes': []
    }
    system = "You are a Next.js developer. Return ONLY a JSON array of strings containing the file paths needed for this project. Do not include markdown or explanations."
    user = f"Project: {plan['title']} (Next.js). Just return the JSON list."
    res = await builder._call_claude(system, user)
    print("Files:", res)

if __name__ == "__main__":
    asyncio.run(test())
