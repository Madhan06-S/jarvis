import asyncio
import builder

async def test():
    plan = {"stack": "html", "title": "Test", "db": "none"}
    files = await builder.generate_project_files(plan, "A simple test app")
    # if the keys are weird, lets just print the raw response by hacking module
    print(files)

if __name__ == "__main__":
    asyncio.run(test())
