import asyncio
import builder

async def test():
    plan = {"stack": "html", "title": "Test", "db": "none"}
    files = await builder.generate_project_files(plan, "A simple test app")
    print(files.keys())
    if "content" in files:
        print("CONTENT:", files["content"][:200])
    if "tool_calls" in files:
        print("TOOL_CALLS:", files["tool_calls"])

if __name__ == "__main__":
    asyncio.run(test())
