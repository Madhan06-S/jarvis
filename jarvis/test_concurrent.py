import asyncio
import builder

async def test():
    plan = {
        'name': 'health-clinic', 'title': 'Health Clinic', 'stack': 'html', 'db': 'none',
        'features': ['booking'], 'theme': 'dark mode', 'pages': [], 'api_routes': []
    }
    print("Generating...")
    # this will spawn 3 concurrent calls
    files = await builder.generate_project_files(plan, "A simple html app")
    print("\nFILES:", list(files.keys()))
    if "index.html" in files:
        print("index.html preview:", files["index.html"][:100].replace("\n", " "))

if __name__ == "__main__":
    asyncio.run(test())
