import asyncio
import builder

async def test():
    plan = {"stack": "html", "title": "Test", "db": "none"}
    system = "Return ONLY a JSON object mapping filenames to file contents."
    user = "Project Test"
    raw = await builder._call_claude(system, user)
    with open("poll_out.json", "w", encoding="utf-8") as f:
        f.write(raw)
    print("Wrote poll_out.json")

if __name__ == "__main__":
    asyncio.run(test())
