import asyncio
import builder

async def test():
    plan = {"stack": "html", "title": "Test", "db": "none"}
    # call claude wrapper directly
    system = "Return ONLY a JSON object: {'index.html': 'content'}"
    user = "Test"
    print("Calling _call_claude directly")
    raw = await builder._call_claude(system, user)
    print("RAW STRING IS:")
    print(raw[:1000])

if __name__ == "__main__":
    asyncio.run(test())
